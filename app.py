import os
from flask import Flask, render_template, request, send_file, jsonify # type: ignore
from werkzeug.utils import secure_filename # type: ignore
import google.generativeai as genai # type: ignore
from docx import Document # type: ignore
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from dotenv import load_dotenv

# تحميل متغيرات البيئة من ملف .env الخفي
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # تحديد أقصى حجم للملفات المرفوعة (16 ميجابايت)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# قراءة مفتاح Gemini API بأمان تام من ملف .env أو بيئة العمل
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("تحذير: لم يتم العثور على مفتاح GEMINI_API_KEY!")

genai.configure(api_key=GEMINI_API_KEY)

# استخدام النموذج الذي اخترته من Google AI Studio
model = genai.GenerativeModel('gemini-3.8-flash')

# دور مساعد أستاذ الفيزياء
PHYSICS_TEACHER_ROLE = """
أنت "مساعد أستاذ الفيزياء الذكي"، خبير تربوي ومختص في تدريس وتبسيط مادة الفيزياء والكيمياء للمراحل التعليمية المختلفة.
مهامك ودورك الأساسي:
1. تحليل صور التجارب العلمية، المسائل الفيزيائية، أو الملفات المرفوعة وشرحها بطريقة تربوية مبسطة.
2. مساعدة المعلم في صياغة وابتكار دروس فيزيائية، تجارب عملية، وتعديلها وفقاً لتعليمات الأستاذ.
3. إعداد واقتراح أسئلة اختبارات (مسائل حسابية، أسئلة فهم وتحليل، صح وخطأ، اختيار من متعدد) مع نموذج الحل والتوجيهات.
4. الرد بأسلوب علمي دقيق، منسق، وواضح باللغة العربية.
"""

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    try:
        user_text = request.form.get('prompt', '')
        export_format = request.form.get('format', 'docx')  # docx أو pdf
        files = request.files.getlist('images')
        
        img_parts = []
        for file in files:
            if file and file.filename != '':
                filename = secure_filename(file.filename)
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(path)
                
                with open(path, 'rb') as f:
                    img_parts.append({
                        'mime_type': file.mimetype,
                        'data': f.read()
                    })

        prompt = f"{PHYSICS_TEACHER_ROLE}\n\nتعليمات الأستاذ وتوجيهاته: {user_text if user_text else 'قم بتحليل محتوى المرفقات وقدم شرحاً فيزيائياً ودرساً منظماً.'}"
        contents = [prompt] + img_parts if img_parts else [prompt]

        # إرسال الطلب إلى النموذج مع معالجة الأخطاء
        response = model.generate_content(contents)
        result_text = response.text if response and hasattr(response, 'text') else "عذراً، لم يتم استلام رد من النموذج."

        # تصدير الملف حسب رغبة الأستاذ (Word أو PDF)
        if export_format == 'pdf':
            file_name = 'physics_lesson.pdf'
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
            
            c = canvas.Canvas(file_path, pagesize=letter)
            width, height = letter
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, height - 50, "Physics Teacher Assistant - Output")
            
            c.setFont("Helvetica", 10)
            text_y = height - 80
            for line in result_text.split('\n'):
                if text_y < 50:
                    c.showPage()
                    text_y = height - 50
                c.drawString(50, text_y, line[:95])
                text_y -= 15
            c.save()
        else:
            file_name = 'physics_lesson.docx'
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
            doc = Document()
            doc.add_heading('مساعد أستاذ الفيزياء - مخرجات الدرس', level=1)
            for line in result_text.split('\n'):
                doc.add_paragraph(line)
            doc.save(file_path)

        return jsonify({
            'status': 'success',
            'response': result_text,
            'download_url': f'/download/{file_name}'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
