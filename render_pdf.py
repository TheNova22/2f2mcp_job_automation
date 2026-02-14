from jinja2 import Environment, FileSystemLoader
import pdfkit # Optional: for PDF generation

# 1. Define your data
data = {
    "basics": {
        "name": "Jane Doe",
        "email": "jane.doe@email.com",
        "phone": "555-0123",
        "location": "New York, NY",
        "linkedin": "linkedin.com/in/janedoe"
    },
    "summary": "Results-driven Software Engineer with 5 years of experience building scalable web apps.",
    "experience": [
        {
            "title": "Senior Developer",
            "company": "Tech Corp",
            "dates": "2021 - Present",
            "highlights": ["Led a team of 5", "Reduced latency by 20%", "Migrated legacy systems to Cloud"]
        },
        {
            "title": "Junior Developer",
            "company": "Startup Inc",
            "dates": "2018 - 2021",
            "highlights": ["Developed UI components", "Optimized database queries"]
        }
    ],
    "skills": ["Python", "Flask", "Jinja2", "SQL", "Docker", "AWS", "Git", "React", "Linux"],
    "education": [
        {
            "institution": "University of Technology",
            "degree": "B.S. Computer Science",
            "year": "2018"
        }
    ]
}

# 2. Set up Jinja2 environment
env = Environment(loader=FileSystemLoader('.'))
template = env.get_template('resume.html')

# 3. Render the HTML
output_html = template.render(data)

# 4. Save to an HTML file
with open("my_resume.html", "w") as f:
    f.write(output_html)

print("HTML resume generated successfully!")

# 5. Optional: Convert to PDF (Requires wkhtmltopdf installed on your system)
# pdfkit.from_string(output_html, "my_resume.pdf")