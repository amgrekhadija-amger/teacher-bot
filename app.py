import os
from flask import Flask, render_template, request, send_file, jsonify # type: ignore
from werkzeug.utils import secure_filename # type: ignore
import google.generativeai as genai # type: ignore
from docx import Document # type: ignore
from reportlab.lib.pagesizes import letter # type: ignore
from reportlab.pdfgen import canvas # type: ignore

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ضع مفتاح API الخاص بك هنا
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
genai.configure(api_key=GEMINI_API_KEY)

# استخدام نموذج ذكاء اصطناعي يدعم النصوص والصور
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """
أنت مساعد تعليمي ذكي مخصص لدعم المعلمين والأطباء الأكاديميين.
مهامك الرئيسية:
1. تحويل الصور والمستندات المرفوعة إلى دروس مرتبة أو ملخصات.
2. إنشاء اختبارات وتدريبات (أسئلة متعددة الخيارات، صح/خطأ، أسئلة مقالية) بناءً على طلب الأستاذ.
3. التعديل على الدروس والأسئلة وحفظ المخرجات في ملفات قابلة للتحميل.
اجعل إجاباتك دائماً منسقة، واضحة، باللغة العربية الفصحى وبأسلوب تربوي ممتاز.
"""

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    user_text = request.form.get('prompt', '')
    files = request.files.getlist('images')
    
    img_parts = []
    for file in files:
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            
            # قراءة الملفات لإرسالها لـ Gemini
            with open(path, 'rb') as f:
                img_parts.append({
                    'mime_type': file.mimetype,
                    'data': f.read()
                })

    # بناء طلب المعالجة للذكاء الاصطناعي
    prompt = f"{SYSTEM_PROMPT}\n\nطلب الأستاذ: {user_text if user_text else 'قم بتحليل واستخراج محتوى الصور وتلخيصه كدرس مرتب.'}"
    contents = [prompt] + img_parts

    try:
        response = model.generate_content(contents)
        result_text = response.text

        # إنشاء ملف Word يحتوي على النتيجة
        doc = Document()
        doc.add_heading('مساعد الأستاذ - المخرجات', level=1)
        for line in result_text.split('\n'):
            doc.add_paragraph(line)
            
        doc_filename = 'output_lesson.docx'
        doc_path = os.path.join(app.config['UPLOAD_FOLDER'], doc_filename)
        doc.save(doc_path)

        return jsonify({
            'status': 'success',
            'response': result_text,
            'word_url': f'/download/{doc_filename}'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/download/<filename>')
def download(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)