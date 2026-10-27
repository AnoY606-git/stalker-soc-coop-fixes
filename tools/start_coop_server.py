"""Экспериментальный выбор 1–8 игроков; сейчас доступен только dry-run.

План команды отделён от запуска. Gate нельзя отключить параметром CLI:
сначала требуется интеграционная проверка полного комплекта lobby data.
Python 3.10+, только стандартная библиотека.
"""

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile


# Снять только после интеграционной проверки совместимого комплекта DLL/config/data.
# Генерация аргументов сама по себе не доказывает готовность к подключению клиентов.
LOBBY_DATA_VERIFIED = False
EXPECTED_ENGINE_SHA256 = "de8e7b892203abc0e7a667b1a56ad0844140f02a82461e8432edc6a3150f2860"
PATCH_DB_NAME = "zzz_coop_player_limit_1_8.db"
EXPECTED_PATCH_DB_SIZE = 471602
EXPECTED_PATCH_DB_SHA256 = "6840f273c8cbad7babfe13cd243c920db7bc8992090f8f377332f169fdbfa12f"
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


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(64 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _casefold_directories(parents: list[Path], name: str) -> list[Path]:
    return [child for parent in parents for child in parent.iterdir()
            if child.name.casefold() == name and child.is_dir()]


def _check_no_loose_overrides(game: Path) -> None:
    # Wine ищет имена без учёта регистра. Проходим только два фиксированных
    # пути; is_dir/iterdir следуют symlink каталогов без рекурсивного обхода.
    roots = _casefold_directories([game], "gamedata")
    configs = _casefold_directories(roots, "configs")
    configs = _casefold_directories(configs, "mp")
    for directory in configs:
        for path in directory.iterdir():
            if path.name.casefold() == "cooperative_game.ltx":
                raise LaunchError(f"Loose override делает комплект неоднозначным: {path}")
    levels = _casefold_directories(roots, "levels")
    for directory in levels:
        for level in directory.iterdir():
            if not level.is_dir():
                continue
            for path in level.iterdir():
                if path.name.casefold() == "level.game":
                    raise LaunchError(f"Loose override делает комплект неоднозначным: {path}")


def check_patch_installation(game: Path) -> None:
    """Только чтение: сверить конкретный candidate DLL/DB и исключить overrides."""
    try:
        _check_no_loose_overrides(game)
        dll = game / "bin" / "xrGame.dll"
        dedicated = game / "bin" / "dedicated" / "xrGame.dll"
        dlls = [dll]
        if dedicated.exists() or dedicated.is_symlink():
            dlls.append(dedicated)
        for path in dlls:
            if not path.is_file() or _file_sha256(path) != EXPECTED_ENGINE_SHA256:
                raise LaunchError(f"Неизвестный или отсутствующий cap8 xrGame.dll (SHA256): {path}")
        allowed = {"gamedata.db0", "gamedata.db1", PATCH_DB_NAME}
        seen = set()
        db_order = []
        addon = game / "addons" / "coop.addon"
        # r: допускает только обычный tar. Переходы между members используют
        # seek; многогигабайтные base/metadata payload не читаются в память.
        with addon.open("rb") as source, tarfile.open(fileobj=source, mode="r:") as archive:
            for member in archive:
                if not re.search(r"\.db[0-9]*$", member.name.rstrip("/"), re.IGNORECASE):
                    continue
                if member.name not in allowed:
                    raise LaunchError(f"Неожиданный DB member в coop.addon: {member.name}")
                if member.name in seen:
                    raise LaunchError(f"Повтор DB member в coop.addon: {member.name}")
                seen.add(member.name)
                if not member.isfile():
                    raise LaunchError(f"DB member должен быть обычным файлом: {member.name}")
                db_order.append(member.name)
                if member.name != PATCH_DB_NAME:
                    continue
                if member.size != EXPECTED_PATCH_DB_SIZE or not 0 < member.size < 1024 ** 2:
                    raise LaunchError(f"Неожиданный размер {PATCH_DB_NAME}: {member.size}")
                payload = archive.extractfile(member)
                if payload is None:
                    raise LaunchError(f"Нельзя прочитать {PATCH_DB_NAME} из coop.addon")
                with payload:
                    data = payload.read(member.size + 1)
                if len(data) != member.size or hashlib.sha256(data).hexdigest() != EXPECTED_PATCH_DB_SHA256:
                    raise LaunchError(f"Неизвестный SHA256 {PATCH_DB_NAME} в coop.addon")
        if PATCH_DB_NAME not in seen:
            raise LaunchError(f"В coop.addon отсутствует обязательный {PATCH_DB_NAME}")
        if db_order != ["gamedata.db0", "gamedata.db1", PATCH_DB_NAME]:
            raise LaunchError(
                "Порядок DB в coop.addon должен быть ровно "
                f"[gamedata.db0, gamedata.db1, {PATCH_DB_NAME}]"
            )
    except (OSError, tarfile.TarError) as error:
        raise LaunchError(f"Не удалось проверить DLL/coop.addon: {error}") from error


def launch(plan: LaunchPlan) -> int:
    """Граница будущего запуска; текущий gate блокирует также вызов из Python."""
    if not LOBBY_DATA_VERIFIED:
        raise LaunchError(LAUNCH_BLOCK_REASON)
    if plan.platform.startswith("linux"):
        prefix = plan.env_overrides.get("WINEPREFIX")
        if prefix is None:
            raise LaunchError("Для реального запуска Linux обязателен явный --wine-prefix.")
        validate_prefix(Path(prefix))
    check_patch_installation(plan.cwd.parent)
    print(f"Ёмкость режима 8; выбранный лимит сессии {plan.players}", flush=True)
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
