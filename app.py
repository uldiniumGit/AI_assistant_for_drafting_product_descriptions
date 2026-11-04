"""CLI entry point for B2B product card draft generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from config import ConfigurationError, Settings, load_dotenv
from openrouter import ApiError, generate_product_card
from product_cards import InputError, load_products, missing_source_fields, render_markdown, source_data, validate_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Черновики B2B-карточек КИП через OpenRouter")
    parser.add_argument("input", nargs="?", default="products.json", help="JSON-файл с исходными товарами")
    parser.add_argument("--format", choices=("markdown", "json"), default="json", help="Формат результата")
    parser.add_argument(
        "--output",
        default="generated_products.json",
        help="Файл результата (по умолчанию generated_products.json; '-' для вывода в консоль)",
    )
    parser.add_argument("--validate-only", action="store_true", help="Проверить JSON без вызова API")
    parser.add_argument("--model", help="Переопределить ID модели OpenRouter")
    return parser.parse_args()


def validate_input(products: list[dict[str, Any]]) -> str:
    report = []
    for product in products:
        source = source_data(product)
        missing = missing_source_fields(source)
        report.append({"product": source["name"], "missing_fields": missing, "valid": not missing})
    return json.dumps(report, ensure_ascii=False, indent=2)


def generate_drafts(products: list[dict[str, Any]], settings: Settings, model: str) -> list[dict[str, Any]]:
    if not settings.api_key:
        raise ConfigurationError(
            "Не задан OPENROUTER_API_KEY. Укажите его в .env; для офлайн-проверки используйте --validate-only."
        )
    drafts = []
    for index, product in enumerate(products, start=1):
        source = source_data(product)
        try:
            result = generate_product_card(
                source,
                api_key=settings.api_key,
                model=model,
                timeout=settings.timeout,
            )
        except ApiError as exc:
            raise ApiError(f"Ошибка API для товара №{index}: {exc}") from exc
        drafts.append(
            {
                "product": product,
                "draft": result,
                "validation_issues": validate_result(result, source),
            }
        )
    return drafts


def format_drafts(drafts: list[dict[str, Any]], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(drafts, ensure_ascii=False, indent=2)
    return "\n\n---\n\n".join(
        render_markdown(item["product"], item["draft"], item["validation_issues"])
        for item in drafts
    )


def write_output(text: str, output_path: str | None) -> None:
    if output_path and output_path != "-":
        try:
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text + "\n", encoding="utf-8")
        except OSError as exc:
            raise InputError(f"Не удалось сохранить результат: {exc}") from exc
    else:
        print(text)


def main() -> int:
    args = parse_args()
    try:
        load_dotenv(Path(__file__).resolve().parent / ".env")
        products = load_products(Path(args.input))
        if args.validate_only:
            output = validate_input(products)
        else:
            settings = Settings.from_environment()
            output = format_drafts(generate_drafts(products, settings, args.model or settings.model), args.format)
        write_output(output, "-" if args.validate_only and args.output == "generated_products.json" else args.output)
    except (InputError, ConfigurationError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2
    except ApiError as exc:
        print(f"Ошибка API: {exc}", file=sys.stderr)
        return 3

    if not args.validate_only:
        print(
            "Внимание: результат является черновиком; проверьте факты по паспорту перед публикацией.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
