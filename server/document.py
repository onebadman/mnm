import io
import os

from docxtpl import DocxTemplate


def escape_data(data: list):
    for i in range(len(data)):
        for j in range(len(data[0])):
            if data[i][j] is None:
                data[i][j] = ""
    return data


def render_table(data: list):
    data = escape_data(data)

    input_file_name = "result_table.docx"
    basedir = os.environ.get('BASE_DIR')
    path = os.path.join(basedir, "", input_file_name)

    template = DocxTemplate(path)

    context = {
        'headers': ['α', 'ε', 'E', 'КСП', 'M'],
        'data': data
    }

    template.render(context)

    file_stream = io.BytesIO()
    template.save(file_stream)
    file_stream.seek(0)

    return file_stream
