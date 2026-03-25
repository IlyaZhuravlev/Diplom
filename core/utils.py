import os
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

def get_font():
    try:
        font_path = r'C:\Windows\Fonts\arial.ttf'
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('Arial', font_path))
            return 'Arial'
    except Exception:
        pass
    return 'Helvetica'

def generate_class_album_pdf(class_id):
    from .models import SchoolClass, PhotoSelection
    try:
        school_class = SchoolClass.objects.get(id=class_id)
    except SchoolClass.DoesNotExist:
        return None

    school = school_class.school
    students = school_class.students.all().order_by('last_name', 'first_name')

    albums_dir = os.path.join(settings.MEDIA_ROOT, 'albums')
    os.makedirs(albums_dir, exist_ok=True)
    
    filename = f"class_{school_class.id}_album.pdf"
    filepath = os.path.join(albums_dir, filename)
    
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    font_name = get_font()

    def draw_template(page_title):
        c.setStrokeColorRGB(0.7, 0.4, 0.1)
        c.setLineWidth(3)
        c.rect(1.5*cm, 1.5*cm, width - 3*cm, height - 3*cm)
        c.rect(1.6*cm, 1.6*cm, width - 3.2*cm, height - 3.2*cm)
        
        c.setFont(font_name, 12)
        c.setFillColorRGB(0.4, 0.3, 0.2)
        c.drawString(2.5*cm, height - 2.5*cm, f"{school.name}")
        c.drawRightString(width - 2.5*cm, height - 2.5*cm, f"Класс {school_class.name} ({school_class.graduation_year})")
        
        c.setFont(font_name, 22)
        c.setFillColorRGB(0.2, 0.15, 0.1)
        c.drawCentredString(width/2, height - 4.5*cm, page_title)

    draw_template("Портретный разворот")
    
    cols = 4
    rows = 6
    margin_x = 2.5 * cm
    margin_y = 6 * cm 
    usable_width = width - 2 * margin_x
    usable_height = height - margin_y - 2.5 * cm
    
    cell_w = usable_width / cols
    cell_h = usable_height / rows
    
    x_idx = 0
    y_idx = 0
    
    for student in students:
        try:
            selection = PhotoSelection.objects.get(student=student, is_confirmed=True)
            portrait = selection.selected_photos.filter(photo_type='portrait').first()
        except PhotoSelection.DoesNotExist:
            portrait = None
            
        x_pos = margin_x + x_idx * cell_w
        y_pos = height - margin_y - (y_idx + 1) * cell_h
        
        if portrait and portrait.image:
            try:
                c.drawImage(portrait.image.path, x_pos + 0.5*cm, y_pos + 1*cm, width=cell_w - 1*cm, height=cell_h - 1.5*cm, preserveAspectRatio=True, anchor='c')
            except Exception:
                pass
                
        c.setFont(font_name, 8)
        c.setFillColorRGB(0.2, 0.15, 0.1)
        c.drawCentredString(x_pos + cell_w/2, y_pos + 0.4*cm, f"{student.last_name} {student.first_name}")
        
        x_idx += 1
        if x_idx >= cols:
            x_idx = 0
            y_idx += 1
            if y_idx >= rows:
                c.showPage()
                draw_template("Портретный разворот (продолжение)")
                y_idx = 0

    c.showPage()
    c.save()
    return f"{settings.MEDIA_URL}albums/{filename}"
