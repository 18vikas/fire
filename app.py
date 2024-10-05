from flask import Flask, request, send_file, redirect, url_for
import shutil
import subprocess
import os
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

app.wsgi_app = ProxyFix( 
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

@app.route('/')
def form():
    return '''
    <form action="/generate-pdf" method="POST">
      <label for="name">Name:</label>
      <input type="text" id="name" name="name" required><br><br>
      <label for="email">Email:</label>
      <input type="email" id="email" name="email" required><br><br>
      <label for="message">Message:</label>
      <textarea id="message" name="message" rows="4" cols="50" required></textarea><br><br>
      <button type="submit">Generate PDF</button>
    </form>
    '''

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']

    # Ensure no LaTeX injection by escaping special characters
    def latex_escape(text):
        return text.replace('&', '\\&').replace('%', '\\%').replace('$', '\\$') \
                   .replace('#', '\\#').replace('_', '\\_').replace('{', '\\{') \
                   .replace('}', '\\}').replace('~', '\\textasciitilde{}') \
                   .replace('^', '\\textasciicircum{}').replace('\\', '\\textbackslash{}')


    # Create the LaTeX file content dynamically
    latex_content = f"""
    \\documentclass{{article}}
    \\usepackage[utf8]{{inputenc}}
    \\usepackage{{pdfpages}}  % To include PDF pages
    \\usepackage{{graphicx}}  % For scaling and positioning
    \\usepackage[margin=1in]{{geometry}}  % Adjust page margins
    \\usepackage{{fancyhdr}}  % For custom header/footer

    \\begin{{document}}

	% Title Section with PDF logo and user information
	\\begin{{titlepage}}
    \\centering
    % Include the PDF as a logo
    \\includepdf[pages=1, width=0.3\\textwidth]{{static/bar.pdf}} \\\\[1em]  % Adjust the width as needed
    
    % Add the document title below the logo
    \\Huge\\textbf{{User Information}} \\\\[2em]
	\\end{{titlepage}}

    \\section*{{User Information}}
    \\textbf{{Name:}} {latex_escape(name)} \\\\
            \\textbf{{Email:}} {latex_escape(email)} \\\\
            \\textbf{{Message:}} {latex_escape(message)} \\\\

            \\end{{document}}
            """



    # Write LaTeX content to a file
    tex_filename = f'tex/{name}.tex'
    with open(tex_filename, 'w') as tex_file:
        tex_file.write(latex_content)

    try:
        # Compile the LaTeX file to a PDF using pdflatex
        subprocess.run(['pdflatex', '-interaction=nonstopmode', tex_filename], check=True)

        # Move the PDF to the 'pdfs/' directory for storage and preview
        pdf_filename = f'{name}.pdf'
        shutil.move(pdf_filename, f'pdfs/{pdf_filename}')

        # Redirect to the preview page
        return redirect(url_for(f'preview_pdf', filename=pdf_filename))
    
    except subprocess.CalledProcessError:
        return "Error: PDF generation failed.", 500
    
    finally:
        # Clean up temporary LaTeX files
        for ext in ['aux', 'log', 'out', 'tex']:
            if os.path.exists(f'{name}.{ext}'):
                os.remove(f'{name}.{ext}')



@app.route('/preview-pdf')
def preview_pdf():
    filename = request.args.get('filename', 'output.pdf')  # Default to 'output.pdf'

    return f'''
    <h1>PDF Preview</h1>
    <iframe src="/pdf/{filename}" width="100%" height="600px"></iframe><br><br>
    <form action="/download-pdf/{filename}" method="POST">
        <button type="submit">Download PDF</button>
    </form>
    '''

@app.route('/pdf/<filename>')
def pdf_preview(filename):
    # Serve the PDF file from the 'pdfs/' folder
    return send_file(f'pdfs/{filename}')

@app.route('/download-pdf/<filename>', methods=['POST'])
def download_pdf(filename):
    # Serve the generated PDF as a file download
    return send_file(f'pdfs/{filename}', as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)

