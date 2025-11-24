"""
FileReader - Módulo para lectura de archivos

Implementa Single Responsibility Principle (SRP):
- Solo responsable de leer archivos y extraer contenido
- No procesa ni valida contenido (eso lo hacen otros módulos)
- Soporte para múltiples formatos: PDF, TXT, DOCX
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


@dataclass
class FileContent:
    """Contenido extraído de un archivo"""
    text: str
    metadata: Dict[str, Any]
    file_type: str
    file_path: str


class FileReadError(Exception):
    """Error al leer archivo"""
    pass


class UnsupportedFileTypeError(FileReadError):
    """Tipo de archivo no soportado"""
    pass


class FileReader:
    """
    Lee archivos de diferentes formatos y extrae su contenido.

    Formatos soportados:
    - PDF (.pdf) - Requiere PyMuPDF
    - Texto plano (.txt)
    - Markdown (.md)
    """

    def __init__(self, encoding: str = 'utf-8'):
        """
        Inicializa el FileReader.

        Args:
            encoding: Encoding para archivos de texto (default: utf-8)
        """
        self.encoding = encoding

    def read(self, file_path: str) -> FileContent:
        """
        Lee un archivo y extrae su contenido.

        Args:
            file_path: Ruta al archivo

        Returns:
            FileContent con el texto extraído y metadata

        Raises:
            FileReadError: Si hay error al leer el archivo
            UnsupportedFileTypeError: Si el formato no es soportado
        """
        path = Path(file_path)

        if not path.exists():
            raise FileReadError(f"Archivo no encontrado: {file_path}")

        if not path.is_file():
            raise FileReadError(f"La ruta no es un archivo: {file_path}")

        file_extension = path.suffix.lower()

        # Determinar método de lectura según extensión
        if file_extension == '.pdf':
            return self._read_pdf(path)
        elif file_extension in ['.txt', '.md']:
            return self._read_text(path)
        else:
            raise UnsupportedFileTypeError(
                f"Formato no soportado: {file_extension}. "
                f"Formatos soportados: .pdf, .txt, .md"
            )

    def _read_pdf(self, path: Path) -> FileContent:
        """
        Lee un archivo PDF y extrae su contenido.

        Args:
            path: Path al archivo PDF

        Returns:
            FileContent con texto extraído

        Raises:
            FileReadError: Si PyMuPDF no está disponible o hay error
        """
        if not PYMUPDF_AVAILABLE:
            raise FileReadError(
                "PyMuPDF no está instalado. Instalar con: pip install pymupdf"
            )

        try:
            doc = fitz.open(str(path))
            content_parts = []

            # Extraer texto de cada página
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                if page_text.strip():  # Solo agregar páginas con contenido
                    content_parts.append(page_text)

            # Extraer metadata
            metadata = {
                "total_pages": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "subject": doc.metadata.get("subject", ""),
                "keywords": doc.metadata.get("keywords", ""),
                "file_size": path.stat().st_size,
                "file_name": path.name
            }

            doc.close()

            content = "\n\n".join(content_parts)

            return FileContent(
                text=content,
                metadata=metadata,
                file_type="pdf",
                file_path=str(path)
            )

        except Exception as e:
            raise FileReadError(f"Error al leer PDF {path.name}: {str(e)}")

    def _read_text(self, path: Path) -> FileContent:
        """
        Lee un archivo de texto plano.

        Args:
            path: Path al archivo de texto

        Returns:
            FileContent con texto extraído

        Raises:
            FileReadError: Si hay error al leer
        """
        try:
            with open(path, 'r', encoding=self.encoding) as f:
                content = f.read()

            metadata = {
                "file_size": path.stat().st_size,
                "file_name": path.name,
                "encoding": self.encoding,
                "line_count": content.count('\n') + 1,
                "char_count": len(content)
            }

            return FileContent(
                text=content,
                metadata=metadata,
                file_type="text",
                file_path=str(path)
            )

        except UnicodeDecodeError:
            # Intentar con encoding alternativo
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    content = f.read()

                metadata = {
                    "file_size": path.stat().st_size,
                    "file_name": path.name,
                    "encoding": "latin-1",
                    "line_count": content.count('\n') + 1,
                    "char_count": len(content)
                }

                return FileContent(
                    text=content,
                    metadata=metadata,
                    file_type="text",
                    file_path=str(path)
                )

            except Exception as e:
                raise FileReadError(
                    f"Error al leer archivo de texto {path.name} "
                    f"(probados encodings: {self.encoding}, latin-1): {str(e)}"
                )

        except Exception as e:
            raise FileReadError(f"Error al leer archivo {path.name}: {str(e)}")

    def get_supported_formats(self) -> list[str]:
        """
        Retorna lista de formatos soportados.

        Returns:
            Lista de extensiones soportadas
        """
        formats = ['.txt', '.md']
        if PYMUPDF_AVAILABLE:
            formats.insert(0, '.pdf')
        return formats

    def is_format_supported(self, file_path: str) -> bool:
        """
        Verifica si un formato es soportado.

        Args:
            file_path: Ruta al archivo

        Returns:
            True si el formato es soportado
        """
        extension = Path(file_path).suffix.lower()
        return extension in self.get_supported_formats()
