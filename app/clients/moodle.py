from urllib.parse import urlparse
import json
import re

import httpx


class MoodleIntegrationError(Exception):
    pass


class MoodleClient:
    def __init__(self, config: dict):
        self.base_url = config["url"].rstrip("/")
        self.public_host = urlparse(config["public_url"]).netloc
        self.integration_token = (config.get("integration_token") or "").strip()
        self.aula_sync_origin = (config.get("aula_sync_origin") or "").strip().rstrip("/")

    def _headers(self, *, include_integration: bool = False) -> dict[str, str]:
        headers = {"Host": self.public_host}
        if include_integration and self.integration_token:
            headers["X-Aula-Sync-Token"] = self.integration_token
        if include_integration and self.aula_sync_origin:
            headers["X-Aula-Sync-Origin"] = self.aula_sync_origin
        return headers

    async def ping_plugin(self) -> dict:
        if not self.integration_token:
            raise MoodleIntegrationError("No hay token de integración configurado")
        url = f"{self.base_url}/local/aulasync/api.php?action=ping"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._headers(include_integration=True))
            if response.is_success:
                return response.json()
            detail = self._parse_error_body(response.text)
            raise MoodleIntegrationError(
                f"Moodle respondió {response.status_code}: {detail}"
            )

    @staticmethod
    def _parse_error_body(text: str) -> str:
        text = text.strip()
        if not text:
            return "Moodle no devolvió detalle del error"
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                if data.get("code"):
                    return str(data["code"])
                if data.get("message"):
                    return str(data["message"])
        except Exception:
            pass
        for pattern in (
            r"errormessage[^>]*>([^<]+)",
            r"alert-danger'>([^<]+)",
            r'class="alert[^"]*"[^>]*>([^<]+)',
        ):
            html_match = re.search(pattern, text, re.IGNORECASE)
            if html_match:
                return html_match.group(1).strip()
        return text[:240]

    async def _post_plugin(self, action: str, data: dict) -> dict:
        url = f"{self.base_url}/local/aulasync/api.php?action={action}"
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                data=data,
                headers=self._headers(include_integration=True),
            )
            if response.is_success:
                return response.json()
            detail = self._parse_error_body(response.text)
            raise MoodleIntegrationError(
                f"Moodle respondió {response.status_code}: {detail}"
            )

    async def _post(self, endpoint: str, data: dict, *, include_integration: bool = True) -> dict:
        url = f"{self.base_url}/integracion/{endpoint}"
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                data=data,
                headers=self._headers(include_integration=include_integration),
            )
            if response.is_success:
                return response.json()
            detail = self._parse_error_body(response.text)
            raise MoodleIntegrationError(
                f"Moodle respondió {response.status_code}: {detail}"
            )

    def _resolve_integration_token(self, token: str | None = None) -> str:
        value = (token or self.integration_token or "").strip()
        if not value:
            raise MoodleIntegrationError("No hay token de integración configurado")
        return value

    async def migrate_course(
        self,
        token: str,
        curso_codigo: str,
        profesor: str,
        grupo: int,
        curso_nombre: str,
        alumnos: list[dict],
        otros_profesores: list[str],
    ) -> dict:
        self._resolve_integration_token(token)
        data: dict = {
            "curso_codigo": curso_codigo,
            "profesor": profesor,
            "grupo": str(grupo),
            "curso_nombre": curso_nombre,
        }
        for i, alumno in enumerate(alumnos):
            for key, value in alumno.items():
                data[f"alumnos[{i}][{key}]"] = str(value) if value is not None else ""
        for i, profe in enumerate(otros_profesores):
            data[f"otros_profesores[{i}]"] = profe
        result = await self._post_plugin("courses", data)
        if isinstance(result, dict) and result.get("status") is False:
            raise MoodleIntegrationError(str(result.get("code") or "Error al migrar curso"))
        return result

    async def migrate_category(
        self,
        token: str,
        idnumber: str,
        name: str,
        parent_idnumber: str = "",
    ) -> dict:
        self._resolve_integration_token(token)
        data = {
            "idnumber": idnumber,
            "name": name,
            "parent_idnumber": parent_idnumber,
        }
        result = await self._post_plugin("categories", data)
        if isinstance(result, dict) and result.get("status") is False:
            raise MoodleIntegrationError(str(result.get("code") or "Error al migrar categoría"))
        return result

    async def sync_categories(self, token: str, categories: list[dict]) -> dict:
        summary = {"created": 0, "updated": 0, "skipped": 0, "errors": 0, "details": []}
        for category in categories:
            try:
                result = await self.migrate_category(
                    token=token,
                    idnumber=category["idnumber"],
                    name=category["name"],
                    parent_idnumber=category.get("parent_idnumber") or "",
                )
                action = str(result.get("action") or "created")
                if action == "created":
                    summary["created"] += 1
                elif action == "updated":
                    summary["updated"] += 1
                else:
                    summary["skipped"] += 1
                summary["details"].append({**category, "action": action, "status": True})
            except MoodleIntegrationError as exc:
                summary["errors"] += 1
                summary["details"].append({**category, "status": False, "error": str(exc)})
                raise
        summary["total"] = len(categories)
        return summary

    async def migrate_user(
        self, token: str, usuario: str, nombres: str, apellidos: str, email: str
    ) -> dict:
        self._resolve_integration_token(token)
        result = await self._post_plugin(
            "users",
            {
                "usuario": usuario,
                "nombres": nombres,
                "apellidos": apellidos,
                "email": email,
            },
        )
        if isinstance(result, dict) and result.get("status") is False:
            raise MoodleIntegrationError(str(result.get("code") or "Error al migrar usuario"))
        return result

    async def enroll(
        self,
        token: str,
        curso_codigo: str,
        profesor: str,
        grupo: int,
        alumnos: list[dict],
    ) -> dict:
        data: dict = {
            "token": self._resolve_integration_token(token),
            "curso_codigo": curso_codigo,
            "profesor": profesor,
            "grupo": str(grupo),
        }
        for i, alumno in enumerate(alumnos):
            for key, value in alumno.items():
                data[f"alumnos[{i}][{key}]"] = str(value) if value is not None else ""
        return await self._post("matricular.php", data)

    async def unenroll(
        self,
        token: str,
        curso_codigo: str,
        profesor: str,
        alumnos: list[dict],
    ) -> dict:
        data: dict = {
            "token": self._resolve_integration_token(token),
            "curso_codigo": curso_codigo,
            "profesor": profesor,
        }
        for i, alumno in enumerate(alumnos):
            for key, value in alumno.items():
                data[f"alumnos[{i}][{key}]"] = str(value) if value is not None else ""
        return await self._post("desmatricular.php", data)

    async def close_cycle(self, token: str, ciclo_academico: str) -> dict:
        return await self._post(
            "cerrarciclo.php",
            {"token": self._resolve_integration_token(token), "ciclo_academico": ciclo_academico},
        )
