"""Экспериментальный выбор 1–8 игроков; сейчас доступен только dry-run.

План команды отделён от запуска. Gate нельзя отключить параметром CLI:
сначала требуется интеграционная проверка полного комплекта lobby data.
Python 3.10+, только стандартная библиотека.
"""

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


# Снять только после интеграционной проверки совместимого комплекта DLL/config/data.
# Генерация аргументов сама по себе не доказывает готовность к подключению клиентов.
LOBBY_DATA_VERIFIED = False
LAUNCH_BLOCK_REASON = (
    "Реальный запуск отключён: комплект lobby data ещё не проверен. "
    "Используйте --dry-run; cap8/config8 без обязательного патча данных лобби "
    "может вызвать выход за границы массива даже у одного клиента."
)


class LaunchError(ValueError):
    """Команду нельзя подготовить или безопасно запустить."""


@dataclass(frozen=True)
class LaunchPlan:
    cwd: Path
    argv: tuple[str, ...]
    env_overrides: dict[str, str]
    platform: str
    players: int


def parse_players(value: str) -> int:
    """Непустой ввод означает явный выбор; EOF не превращается в default."""
    try:
        players = int(value)
    except ValueError as error:
        raise LaunchError("Количество игроков должно быть целым числом от 1 до 8.") from error
    if not 1 <= players <= 8:
        raise LaunchError("Количество игроков должно быть целым числом от 1 до 8.")
    return players


def build_launch_plan(
    game: Path,
    players: int,
    *,
    platform: str,
    wine: str | None = None,
    wine_prefix: Path | None = None,
    nosound: bool = False,
) -> LaunchPlan:
    """Чисто построить argv для явно выбранной платформы, без файловых операций."""
    if type(players) is not int or not 1 <= players <= 8:
        raise LaunchError("Количество игроков должно быть целым числом от 1 до 8.")
    if not game.is_absolute():
        raise LaunchError("Для плана требуется абсолютный путь игры.")
    engine = str(game / "bin" / "dedicated" / "xrEngine.exe")
    environment = {}
    if platform == "win32":
        if wine is not None or wine_prefix is not None:
            raise LaunchError("В Windows параметры --wine и --wine-prefix не используются.")
        command = [engine]
    elif platform.startswith("linux"):
        if not wine:
            raise LaunchError("Для Linux требуется путь к Wine.")
        command = [wine, engine]
        if wine_prefix is not None:
            if not wine_prefix.is_absolute():
                raise LaunchError("Для плана требуется абсолютный путь Wine prefix.")
            environment["WINEPREFIX"] = str(wine_prefix)
    else:
        raise LaunchError("Поддерживаются только Windows и Linux с Wine.")
    command.extend([
        "-i", "-noprefetch", "-nointro", "-fsltx", "..\\fsgame_s.ltx",
        "-use_all_spawn", "-addon=coop.addon",
    ])
    if nosound:
        command.append("-nosound")
    # Это один аргумент argv: буквальные кавычки и shell здесь не нужны.
    command.extend([
        "-start",
        "server(coop_l01_escape/coop/hname=ShadowCoop/maxplayers="
        f"{players}/public=0/minplayers=1/portsv=5495) client(localhost)",
    ])
    return LaunchPlan(game / "bin", tuple(command), environment, platform, players)


def validate_installation(game: Path) -> None:
    """Проверить наличие входов; это не проверка совместимости игровых данных."""
    for relative in ("bin/dedicated/xrEngine.exe", "fsgame_s.ltx", "addons/coop.addon"):
        path = game / relative
        if not path.is_file():
            raise LaunchError(f"Отсутствует необходимый файл игры: {path}")


def resolve_wine(value: str | None) -> str:
    candidate = value if value is not None else shutil.which("wine")
    if not candidate:
        raise LaunchError("Wine не найден в PATH; задайте --wine /путь/к/wine.")
    path = Path(candidate).expanduser().resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise LaunchError(f"Wine отсутствует или не является исполняемым файлом: {path}")
    return str(path)


def validate_prefix(prefix: Path) -> None:
    """Не позволить Wine принять пустой каталог за новый prefix."""
    if not prefix.is_absolute():
        raise LaunchError("Wine prefix должен иметь абсолютный путь.")
    if prefix.resolve() == (Path.home() / ".wine").resolve():
        raise LaunchError("Пользовательский ~/.wine запрещён; выберите отдельный Wine prefix.")
    if not all((prefix / name).is_file() for name in ("system.reg", "user.reg")) or not all(
        (prefix / name).is_dir() for name in ("drive_c", "dosdevices")
    ):
        raise LaunchError(f"Нужен существующий инициализированный Wine prefix: {prefix}")


def launch(plan: LaunchPlan) -> int:
    """Граница будущего запуска; текущий gate блокирует также вызов из Python."""
    if not LOBBY_DATA_VERIFIED:
        raise LaunchError(LAUNCH_BLOCK_REASON)
    if plan.platform.startswith("linux"):
        prefix = plan.env_overrides.get("WINEPREFIX")
        if prefix is None:
            raise LaunchError("Для реального запуска Linux обязателен явный --wine-prefix.")
        validate_prefix(Path(prefix))
    environment = os.environ.copy()
    environment.update(plan.env_overrides)
    result = subprocess.run(list(plan.argv), cwd=plan.cwd, env=environment, shell=False)
    return result.returncode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Экспериментальный выбор 1–8 игроков. Сейчас доступен только --dry-run: "
            "комплект lobby data ещё не проверен. Карта coop_l01_escape; public=0."
        )
    )
    parser.add_argument("--game", required=True, type=Path, help="корневой каталог игры")
    parser.add_argument("--players", help="целое 1–8; без параметра — ввод, Enter выбирает 5")
    parser.add_argument("--dry-run", action="store_true", help="JSON команды без запуска и записи файлов")
    parser.add_argument("--wine", help="исполняемый файл Wine; по умолчанию поиск wine в PATH")
    parser.add_argument("--wine-prefix", type=Path, help="существующий отдельный Wine prefix для Linux")
    parser.add_argument("--nosound", action="store_true", help="явно отключить звук для диагностики")
    args = parser.parse_args(argv)
    try:
        if not args.dry_run and not LOBBY_DATA_VERIFIED:
            raise LaunchError(LAUNCH_BLOCK_REASON)
        if args.players is None:
            # Prompt идёт в stderr: stdout dry-run остаётся корректным JSON.
            print("Количество игроков [1–8], Enter = 5: ", end="", file=sys.stderr, flush=True)
            try:
                answer = input().strip()
            except (EOFError, KeyboardInterrupt) as error:
                raise LaunchError("Ввод прерван; укажите --players 1..8 явно.") from error
            players = parse_players(answer) if answer else 5
        else:
            players = parse_players(args.players)
        game = args.game.expanduser().resolve()
        validate_installation(game)
        prefix = args.wine_prefix.expanduser().resolve() if args.wine_prefix is not None else None
        if prefix is not None and sys.platform.startswith("linux"):
            validate_prefix(prefix)
        wine = resolve_wine(args.wine) if sys.platform.startswith("linux") else args.wine
        plan = build_launch_plan(
            game, players, platform=sys.platform, wine=wine, wine_prefix=prefix, nosound=args.nosound
        )
        if args.dry_run:
            print(json.dumps({
                "cwd": str(plan.cwd),
                "argv": list(plan.argv),
                "environment": {"inherit": True, "overrides": plan.env_overrides},
                "players": players,
                "map": "coop_l01_escape",
                "launch_allowed": False,
                "launch_block_reason": LAUNCH_BLOCK_REASON,
            }, ensure_ascii=False, indent=2))
            return 0
        return launch(plan)
    except (LaunchError, OSError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    # CLI всегда выдаёт UTF-8, включая JSON, prompt, help и сообщения об ошибках.
    # Импорт модуля не меняет потоки вызывающего приложения.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())
