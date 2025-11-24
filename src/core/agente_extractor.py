"""
APFExtractor - Extractor de información de puestos APF

Implementa principios SOLID:
- Single Responsibility: Solo orquesta la extracción de datos
- Dependency Inversion: Depende de interfaces abstractas (ILLMProvider)
- Open/Closed: Extensible mediante DI sin modificar código

Refactorizado desde v4 aplicando DI y separación de responsabilidades.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json

from ..interfaces.llm_provider import ILLMProvider, LLMRequest
from .file_reader import FileReader, FileContent
from .prompt_builder import PromptBuilder, ExtractionMode
from .data_validator import DataValidator, ValidationResult


class ExtractionError(Exception):
    """Error durante extracción de información"""
    pass


class APFExtractor:
    """
    Extractor de información de puestos de la APF.

    Este extractor orquesta el proceso completo:
    1. Lee el archivo (via FileReader)
    2. Construye el prompt (via PromptBuilder)
    3. Llama al LLM (via ILLMProvider)
    4. Valida el resultado (via DataValidator)

    Todas las dependencias se inyectan, permitiendo fácil testing y extensión.
    """

    def __init__(
        self,
        llm_provider: ILLMProvider,
        file_reader: Optional[FileReader] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        data_validator: Optional[DataValidator] = None,
        enable_logging: bool = True
    ):
        """
        Inicializa el extractor con sus dependencias.

        Args:
            llm_provider: Provider de LLM (requerido)
            file_reader: Reader de archivos (opcional, se crea uno por defecto)
            prompt_builder: Constructor de prompts (opcional, se crea uno por defecto)
            data_validator: Validador de datos (opcional, se crea uno por defecto)
            enable_logging: Habilitar logging
        """
        # Dependencias inyectadas
        self.llm_provider = llm_provider
        self.file_reader = file_reader or FileReader()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.data_validator = data_validator or DataValidator()

        self.enable_logging = enable_logging

    def extract_from_file(
        self,
        file_path: str,
        mode: ExtractionMode = ExtractionMode.INTELLIGENT,
        max_tokens: int = 4000,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Extrae información de un archivo de puesto.

        Args:
            file_path: Ruta al archivo
            mode: Modo de extracción (fast, intelligent, thorough)
            max_tokens: Tokens máximos para LLM
            temperature: Temperatura del LLM

        Returns:
            Diccionario con información extraída y validada

        Raises:
            ExtractionError: Si hay error en el proceso
        """
        if self.enable_logging:
            print(f"\n[Extractor] Procesando: {Path(file_path).name}")
            print(f"[Extractor] Modo: {mode.value}")

        # Paso 1: Leer archivo
        try:
            file_content = self.file_reader.read(file_path)
            if self.enable_logging:
                print(f"[Extractor] Archivo leído: {len(file_content.text)} caracteres")
        except Exception as e:
            raise ExtractionError(f"Error al leer archivo: {str(e)}")

        # Paso 2: Construir prompt
        try:
            prompt = self.prompt_builder.build_extraction_prompt(
                content=file_content.text,
                mode=mode
            )
            if self.enable_logging:
                print(f"[Extractor] Prompt construido: {len(prompt)} caracteres")
        except Exception as e:
            raise ExtractionError(f"Error al construir prompt: {str(e)}")

        # Paso 3: Llamar al LLM
        try:
            request = LLMRequest(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )

            extracted_data = self.llm_provider.complete_json(request)

            if self.enable_logging:
                print(f"[Extractor] Extracción completada")
        except Exception as e:
            raise ExtractionError(f"Error en llamada a LLM: {str(e)}")

        # Paso 4: Validar resultado
        try:
            validation_result = self.data_validator.validate_extraction(extracted_data)

            if self.enable_logging:
                print(f"[Extractor] Validación: {validation_result.error_count} errores, "
                      f"{validation_result.warning_count} warnings")

                if validation_result.errors:
                    print("[Extractor] Errores encontrados:")
                    for error in validation_result.errors[:3]:  # Mostrar máximo 3
                        print(f"  - {error.field}: {error.message}")

            # Retornar resultado con metadata
            return {
                "status": "success" if validation_result.is_valid else "partial",
                "data": extracted_data,
                "validation": {
                    "is_valid": validation_result.is_valid,
                    "error_count": validation_result.error_count,
                    "warning_count": validation_result.warning_count,
                    "issues": [
                        {
                            "field": issue.field,
                            "severity": issue.severity.value,
                            "message": issue.message
                        }
                        for issue in validation_result.issues
                    ]
                },
                "metadata": {
                    "file_name": file_content.metadata.get("file_name"),
                    "file_type": file_content.file_type,
                    "extraction_mode": mode.value
                }
            }

        except Exception as e:
            raise ExtractionError(f"Error en validación: {str(e)}")

    def extract_from_text(
        self,
        text: str,
        mode: ExtractionMode = ExtractionMode.INTELLIGENT,
        max_tokens: int = 4000,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """
        Extrae información directamente de texto (sin archivo).

        Args:
            text: Texto del documento
            mode: Modo de extracción
            max_tokens: Tokens máximos para LLM
            temperature: Temperatura del LLM

        Returns:
            Diccionario con información extraída

        Raises:
            ExtractionError: Si hay error en el proceso
        """
        if self.enable_logging:
            print(f"\n[Extractor] Procesando texto directo ({len(text)} caracteres)")

        # Construir prompt
        try:
            prompt = self.prompt_builder.build_extraction_prompt(
                content=text,
                mode=mode
            )
        except Exception as e:
            raise ExtractionError(f"Error al construir prompt: {str(e)}")

        # Llamar al LLM
        try:
            request = LLMRequest(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )

            extracted_data = self.llm_provider.complete_json(request)
        except Exception as e:
            raise ExtractionError(f"Error en llamada a LLM: {str(e)}")

        # Validar resultado
        try:
            validation_result = self.data_validator.validate_extraction(extracted_data)

            if self.enable_logging:
                print(f"[Extractor] Validación: {validation_result.error_count} errores")

            return {
                "status": "success" if validation_result.is_valid else "partial",
                "data": extracted_data,
                "validation": {
                    "is_valid": validation_result.is_valid,
                    "error_count": validation_result.error_count,
                    "warning_count": validation_result.warning_count,
                    "issues": [
                        {
                            "field": issue.field,
                            "severity": issue.severity.value,
                            "message": issue.message
                        }
                        for issue in validation_result.issues
                    ]
                },
                "metadata": {
                    "extraction_mode": mode.value,
                    "source": "text"
                }
            }

        except Exception as e:
            raise ExtractionError(f"Error en validación: {str(e)}")

    def get_info(self) -> Dict[str, Any]:
        """
        Retorna información del extractor y sus dependencias.

        Returns:
            Dict con información de configuración
        """
        return {
            "extractor_version": "5.0.0",
            "llm_provider": self.llm_provider.get_model_info(),
            "file_reader": {
                "supported_formats": self.file_reader.get_supported_formats()
            },
            "extraction_modes": [mode.value for mode in ExtractionMode],
            "logging_enabled": self.enable_logging
        }
