# data_parser.py
import re
from abc import ABC, abstractmethod
from docx import Document


class Parser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> list:
        pass


class ServiceCallParser(Parser):
    def parse(self, file_path: str) -> list:
        with open(file_path, "r") as file:
            text = file.read()
        service_calls = self.parse_service_calls(text)
        return [{"filename": file_path, "text": service_calls}]

    def parse_service_calls(self, text: str) -> list:
        service_calls = []
        current_call = None
        current_interaction = None

        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("1"):
                if current_call:
                    if current_interaction:
                        current_call["interactions"].append(current_interaction)
                        current_interaction = None
                    service_calls.append(current_call)
                current_call = {"ServiceCallID": line[1:].strip(), "interactions": []}
            elif line.startswith("2"):
                content = line[1:].strip()
                if content.startswith("_" * 10):
                    if current_interaction:
                        current_call["interactions"].append(current_interaction)
                    current_interaction = {"message": ""}
                elif "נוסף על ידי" in content and "ב-" in content:
                    match = re.search(r"נוסף על ידי (.+?) ב- (.+?) :", content)
                    if match:
                        if current_interaction:
                            current_call["interactions"].append(current_interaction)
                        current_interaction = {
                            "added_by": match.group(1).strip(),
                            "timestamp": match.group(2).strip(),
                            "message": "",
                        }
                else:
                    if current_interaction:
                        if current_interaction["message"]:
                            current_interaction["message"] += "\n"
                        current_interaction["message"] += content
                    else:
                        current_interaction = {"message": content}

        if current_interaction:
            current_call["interactions"].append(current_interaction)
        if current_call:
            service_calls.append(current_call)

        return service_calls


# class ProcedureParser(Parser):
#     def parse(self, file_path: str) -> list:
#         document = Document(file_path)
#         chunks = self.chunk_procedures(document, file_path)
#         return chunks

#     def chunk_procedures(
#         self, document: Document, file_path: str, chunk_size: int = 100
#     ) -> list:
#         chunks = []
#         current_chunk = []
#         current_plain_chunk = []
#         current_length = 0
#         section_heading = None
#         section_heading_plain = None

#         for para in document.paragraphs:
#             text = para.text.strip()
#             if text:
#                 plain_text = text
#                 formatted_text = self.format_paragraph(para)
#                 if para.style.name.startswith("Heading"):
#                     if current_chunk:
#                         chunk_text = " ".join(current_chunk)
#                         chunk_plain_text = " ".join(current_plain_chunk)
#                         if section_heading:
#                             chunk_text = f"{section_heading}\n{chunk_text}"
#                             chunk_plain_text = (
#                                 f"{section_heading_plain}\n{chunk_plain_text}"
#                             )
#                             section_heading = None  # Reset heading after using it once
#                             section_heading_plain = None
#                         chunks.append(
#                             {
#                                 "filename": file_path,
#                                 "heading": section_heading,
#                                 "plain_text": chunk_plain_text,
#                                 "formatted_text": chunk_text,
#                             }
#                         )
#                         current_chunk = []
#                         current_plain_chunk = []
#                         current_length = 0
#                     section_heading = formatted_text
#                     section_heading_plain = plain_text
#                 else:
#                     words = text.split()
#                     if current_length + len(words) > chunk_size:
#                         chunk_text = " ".join(current_chunk)
#                         chunk_plain_text = " ".join(current_plain_chunk)
#                         if section_heading:
#                             chunk_text = f"{section_heading}\n{chunk_text}"
#                             chunk_plain_text = (
#                                 f"{section_heading_plain}\n{chunk_plain_text}"
#                             )
#                             section_heading = None  # Reset heading after using it once
#                             section_heading_plain = None
#                         chunks.append(
#                             {
#                                 "filename": file_path,
#                                 "heading": section_heading,
#                                 "plain_text": chunk_plain_text,
#                                 "formatted_text": chunk_text,
#                             }
#                         )
#                         current_chunk = [formatted_text]
#                         current_plain_chunk = [plain_text]
#                         current_length = len(words)
#                     else:
#                         current_chunk.append(formatted_text)
#                         current_plain_chunk.append(plain_text)
#                         current_length += len(words)

#         if current_chunk:
#             chunk_text = " ".join(current_chunk)
#             chunk_plain_text = " ".join(current_plain_chunk)
#             if section_heading:
#                 chunk_text = f"{section_heading}\n{chunk_text}"
#                 chunk_plain_text = f"{section_heading_plain}\n{chunk_plain_text}"
#             chunks.append(
#                 {
#                     "filename": file_path,
#                     "heading": section_heading,
#                     "plain_text": chunk_plain_text,
#                     "formatted_text": chunk_text,
#                 }
#             )

#         return chunks

#     def format_paragraph(self, para):
#         runs = []
#         for run in para.runs:
#             text = run.text
#             if run.bold:
#                 text = f"<strong>{text}</strong>"
#             if run.italic:
#                 text = f"<em>{text}</em>"
#             if run.underline:
#                 text = f"<u>{text}</u>"
#             if run.font.color.rgb:
#                 color = run.font.color.rgb
#                 text = f'<span style="color: rgb({color[0]}, {color[1]}, {color[2]});">{text}</span>'
#             runs.append(text)

#         formatted_text = "".join(runs)
#         if para.style.name.startswith("Heading"):
#             level = int(para.style.name[-1])
#             formatted_text = f"<h{level}>{formatted_text}</h{level}>"
#         elif para.style.name == "List Paragraph":
#             formatted_text = f"<li>{formatted_text}</li>"

#         return formatted_text

class ProcedureParser(Parser):
    def parse(self, file_path: str) -> list:
        document = Document(file_path)
        chunks = self.chunk_procedures(document, file_path)
        return chunks

    def chunk_procedures(self, document: Document, file_path: str, chunk_size: int = 100) -> list:
        chunks = []
        current_chunk = []
        current_plain_chunk = []
        current_length = 0
        section_heading = None
        section_heading_plain = None

        for para in document.paragraphs:
            text = para.text.strip()
            if text:
                plain_text = text
                formatted_text = self.format_paragraph(para)
                if para.style.name.startswith("Heading"):
                    if current_chunk:
                        self.add_chunk(
                            chunks, current_chunk, current_plain_chunk,
                            section_heading, section_heading_plain, file_path
                        )
                        current_chunk = []
                        current_plain_chunk = []
                        current_length = 0
                    section_heading = formatted_text
                    section_heading_plain = plain_text
                else:
                    words = text.split()
                    if current_length + len(words) > chunk_size:
                        self.add_chunk(
                            chunks, current_chunk, current_plain_chunk,
                            section_heading, section_heading_plain, file_path
                        )
                        current_chunk = [formatted_text]
                        current_plain_chunk = [plain_text]
                        current_length = len(words)
                    else:
                        current_chunk.append(formatted_text)
                        current_plain_chunk.append(plain_text)
                        current_length += len(words)

        if current_chunk:
            self.add_chunk(
                chunks, current_chunk, current_plain_chunk,
                section_heading, section_heading_plain, file_path
            )

        # Now handle tables
        for table in document.tables:
            table_text = self.format_table(table)
            chunks.append({
                "filename": file_path,
                "heading": None,
                "plain_text": table_text,
                "formatted_text": table_text,
            })

        return chunks

    def add_chunk(self, chunks, current_chunk, current_plain_chunk, section_heading, section_heading_plain, file_path):
        chunk_text = " ".join(current_chunk)
        chunk_plain_text = " ".join(current_plain_chunk)
        if section_heading:
            chunk_text = f"{section_heading}\n{chunk_text}"
            chunk_plain_text = f"{section_heading_plain}\n{chunk_plain_text}"
        chunks.append({
            "filename": file_path,
            "heading": section_heading,
            "plain_text": chunk_plain_text,
            "formatted_text": chunk_text,
        })

    def format_paragraph(self, para):
        runs = []
        for run in para.runs:
            text = run.text
            if run.bold:
                text = f"<strong>{text}</strong>"
            if run.italic:
                text = f"<em>{text}</em>"
            if run.underline:
                text = f"<u>{text}</u>"
            if run.font.color.rgb:
                color = run.font.color.rgb
                text = f'<span style="color: rgb({color[0]}, {color[1]}, {color[2]});">{text}</span>'
            runs.append(text)

        formatted_text = "".join(runs)
        if para.style.name.startswith("Heading"):
            level = int(para.style.name[-1])
            formatted_text = f"<h{level}>{formatted_text}</h{level}>"
        elif para.style.name == "List Paragraph":
            formatted_text = f"<li>{formatted_text}</li>"

        return formatted_text

    def format_table(self, table):
        rows = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            rows.append(cells)
        table_html = "<table>"
        for row in rows:
            table_html += "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        table_html += "</table>"
        return table_html