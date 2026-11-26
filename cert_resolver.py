from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

PORTAL_HOSTS = ("https://xn--h1adlhdnlo2c.xn--p1ai", "https://datalesson.ru")
USER_AGENT = "Mozilla/5.0"
REQUEST_TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class LessonTarget:
    slug: str
    session_id: str


@dataclass(frozen=True)
class CertificateResult:
    url: str
    slug: str
    session_id: str
    verified: bool


def parse_lesson_url(raw_url: str, slug_override: str = "") -> LessonTarget:
    text = raw_url.strip()
    if not text:
        raise ValueError("Введите ссылку на урок.")

    if "://" not in text:
        text = "https://" + text

    parsed = urlparse(text)
    if not parsed.netloc:
        raise ValueError("Некорректная ссылка.")

    query = parse_qs(parsed.query.replace("?", "&"))
    session_values = query.get("session_id")
    if not session_values or not session_values[0].strip():
        raise ValueError("В ссылке отсутствует параметр session_id.")

    session_id = session_values[0].strip()
    slug = slug_override.strip() or extract_slug(parsed.netloc, parsed.path)
    if not slug:
        raise ValueError("Не удалось определить код урока из ссылки. Укажите его вручную.")

    return LessonTarget(slug=slug, session_id=session_id)


def extract_slug(netloc: str, path: str) -> str:
    host = netloc.split(":")[0].lower()
    segments = [part for part in path.split("/") if part]

    if len(segments) >= 2 and segments[0] == "lessons":
        return segments[1]

    if host.endswith(".datalesson.ru"):
        subdomain = host[: -len(".datalesson.ru")]
        if subdomain and subdomain != "www":
            return subdomain

    return ""


def verify_certificate_url(target: LessonTarget) -> CertificateResult:
    last_error = ""
    for base_url in PORTAL_HOSTS:
        cert_url = f"{base_url}/lessons/{target.slug}/certificate?session_id={target.session_id}"
        try:
            if check_certificate_page(cert_url):
                return CertificateResult(
                    url=cert_url,
                    slug=target.slug,
                    session_id=target.session_id,
                    verified=True,
                )
            last_error = f"Страница {cert_url} не похожа на страницу сертификата."
        except HTTPError as exc:
            last_error = f"Сервер вернул HTTP {exc.code} для {cert_url}."
        except (URLError, TimeoutError) as exc:
            last_error = f"Ошибка сети при проверке {cert_url}: {exc}"

    raise RuntimeError(last_error or "Не удалось проверить страницу сертификата.")


def check_certificate_page(url: str) -> bool:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        if response.status != 200:
            return False
        body = response.read().decode("utf-8", errors="ignore")
        return "certificate-page" in body or "Поздравляем" in body
