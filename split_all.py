import os
import re
import codecs

os.makedirs('static/js', exist_ok=True)

html_files = [
    'templates/manage.html',
    'templates/login.html',
    'templates/register.html',
    'templates/admin.html',
    'templates/verify_email.html',
    'templates/admin/approve.html',
    'templates/approve.html'
]

for file_path in html_files:
    if not os.path.exists(file_path):
        continue
        
    with codecs.open(file_path, 'r', 'utf-8') as f:
        content = f.read()
    
    # Tìm thẻ block scripts if exists
    block_scripts_start = content.find('{% block scripts %}')
    if block_scripts_start == -1:
        block_scripts_start = 0

    # Tìm nội dung trong <script>...</script>
    scripts = re.findall(r'<script>(.*?)</script>', content[block_scripts_start:], flags=re.DOTALL)
    
    # Chỉ bóc tách block JS nếu nó dài hơn 30 dòng và KHÔNG chứa Jinja code {{ }} hay {% %}
    extracted_js = ""
    for s in scripts:
        if len(s.strip().split('\n')) > 15:
            if '{{' in s or '{%' in s:
                continue # Bỏ qua script chứa biến cục bộ Jinja
            extracted_js += s.strip() + "\n\n"
            # Cắt bỏ script này khỏi HTML
            content = content.replace(f'<script>{s}</script>', '')

    if extracted_js:
        base_name = os.path.basename(file_path).replace('.html', '.js')
        out_path = f'static/js/{base_name}'
        with codecs.open(out_path, 'w', 'utf-8') as f:
            f.write(extracted_js)
        
        # Thêm file JS vào lại block scripts
        if '{% block scripts %}' in content:
            content = content.replace('{% block scripts %}', f"{{% block scripts %}}\n<script src=\"{{{{ url_for('static', filename='js/{base_name}') }}}}?v=1.0\"></script>")
        else:
            content += f"\n<script src=\"{{{{ url_for('static', filename='js/{base_name}') }}}}?v=1.0\"></script>\n"
            
        with codecs.open(file_path, 'w', 'utf-8') as f:
            f.write(content)
        print(f"Extracted JS from {file_path} to {out_path}")

print("Scanning completed.")
