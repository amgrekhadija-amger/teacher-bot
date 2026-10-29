import os
from flask import Flask, render_template, request, send_file, jsonify # type: ignore
from werkzeug.utils import secure_filename # type: ignore
from google import genai # type: ignore
from docx import Document # type: ignore
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from dotenv import load_dotenv

# تحميل متغيرات البيئة من ملف .env الخفي
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # أقصى حجم للملفات 16 ميجابايت
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# قراءة مفتاح Gemini API بأمان باستخدام الكلاينت الحديث
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("تحذير: لم يتم العثور على مفتاح GEMINI_API_KEY في متغيرات البيئة!")

client = genai.Client(api_key=GEMINI_API_KEY)

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
        export_format = request.form.get('format', 'docx')
        files = request.files.getlist('images')
        
        # تجهيز نص الإدخال الموجه للنموذج
        full_input = f"{PHYSICS_TEACHER_ROLE}\n\nتعليمات الأستاذ وتوجيهاته: {user_text if user_text else 'قم بتحليل محتوى المرفقات وقدم شرحاً فيزيائياً ودرساً منظماً.'}"
        
        # إعدادات التوليد المطلوبة للنموذج الحديث
        tools = [{'type': 'google_search'}]
        generation_config = {
            'max_output_tokens': 65536,
            'thinking_level': 'medium',
        }

        # استخدام الطريقة الحديثة للتعامل مع التفاعل (Interactions API)
        interaction = client.interactions.create(
            model='models/gemini-3.8-flash',
            input=full_input,
            tools=tools,
            generation_config=generation_config,
        )

        result_text = interaction.steps[-1] if interaction and interaction.steps else "عذراً، لم يتم استلام رد من النموذج."

        if export_format == 'pdf':
            file_name = 'physics_lesson.pdf'
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
            
            c = canvas.Canvas(file_path, pagesize=letter)
            width, height = letter
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, height - 50, "Physics Teacher Assistant - Output")
            
            c.setFont("Helvetica", 10)
            text_y = height - 80
            for line in str(result_text).split('\n'):
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
            for line in str(result_text).split('\n'):
                doc.add_paragraph(line)
            doc.save(file_path)

        return jsonify({
            'status': 'success',
            'response': str(result_text),
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
