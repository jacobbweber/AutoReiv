"""
AutoReiv Unified CLI Entry Point & Command Dispatcher [REQ-DEPLOY-001, REQ-DEPLOY-002].
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import List, Optional

from src.application.kernel.agent_kernel import AgentKernel
from src.application.routines.executor import RoutineExecutor
from src.application.settings.hardware_calculator import HardwareFitCalculator
from src.application.telemetry.collector import TelemetryCollector
from src.domain.kernel.models import KernelEventType
from src.domain.routines.manifests import BUILTIN_ROUTINES
from src.infrastructure.agents.registry import BuiltinAgentRegistry
from src.infrastructure.data.backup import DataDirBackupService, DataDirRestoreError
from src.infrastructure.data.resolver import bootstrap_data_dir
from src.infrastructure.gateway.factory import GatewayProviderFactory
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def build_parser() -> argparse.ArgumentParser:
    """Constructs the command-line argument parser for AutoReiv."""
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--data-dir",
        default=None,
        help="User data directory (default: $AUTOREIV_DATA_DIR, else platform default)",
    )
    common_parser.add_argument(
        "--db-path",
        default=None,
        help="Path to SQLite state database (default: $DATA_DIR/autoreiv.db or $AUTOREIV_DB_PATH)",
    )
    common_parser.add_argument(
        "--wiki-path",
        default=None,
        help="Root path for PARA-Wiki markdown storage (default: $DATA_DIR/wiki or $AUTOREIV_WIKI_PATH)",
    )

    parser = argparse.ArgumentParser(
        prog="autoreiv",
        description="AutoReiv: Local-First Hybrid AI Agent Control Plane & Assistant Platform",
        parents=[common_parser],
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # serve
    serve_p = subparsers.add_parser(
        "serve",
        parents=[common_parser],
        help="Start the FastAPI web server & background routine engine",
    )
    serve_p.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"), help="Host IP to bind (default: 0.0.0.0)")
    serve_p.add_argument(
        "--port", type=int, default=int(os.environ.get("PORT", "8000")), help="Port to listen on (default: 8000)"
    )
    serve_p.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    # status
    subparsers.add_parser(
        "status",
        parents=[common_parser],
        help="Display host hardware specs, database connectivity, and agent status",
    )

    # routine
    routine_p = subparsers.add_parser(
        "routine",
        parents=[common_parser],
        help="Manage and execute background routines",
    )
    routine_sub = routine_p.add_subparsers(dest="routine_command", help="Routine subcommands")
    routine_sub.add_parser("list", parents=[common_parser], help="List all registered autonomous routines")
    run_p = routine_sub.add_parser(
        "run", parents=[common_parser], help="Trigger a single routine execution immediately"
    )
    run_p.add_argument("routine_id", help="ID of the routine to execute (e.g. morning-briefing)")

    # chat
    chat_p = subparsers.add_parser(
        "chat",
        parents=[common_parser],
        help="Start an interactive terminal chat session with an agent",
    )
    chat_p.add_argument("agent_id", default="assistant", nargs="?", help="Target Agent ID (default: assistant)")

    # backup / restore [REQ-DATA-007, REQ-DATA-008]
    backup_p = subparsers.add_parser(
        "backup",
        parents=[common_parser],
        help="Zip the resolved data dir (db, wiki, skills) to one archive",
    )
    backup_p.add_argument(
        "dest",
        nargs="?",
        default=None,
        help="Destination zip (default: $DATA_DIR/backups/autoreiv-data-<timestamp>.zip)",
    )
    restore_p = subparsers.add_parser(
        "restore",
        parents=[common_parser],
        help="Replace the resolved data dir from a backup zip",
    )
    restore_p.add_argument("src", help="Source backup zip")
    restore_p.add_argument(
        "--yes",
        action="store_true",
        help="Confirm replace-the-tree restore (required; cancel is a no-op)",
    )

    return parser


def apply_storage_args(args: argparse.Namespace):
    """Apply CLI path flags, then resolve and copy-migrate."""
    if getattr(args, "data_dir", None):
        os.environ["AUTOREIV_DATA_DIR"] = args.data_dir
    if getattr(args, "db_path", None):
        os.environ["AUTOREIV_DB_PATH"] = args.db_path
    if getattr(args, "wiki_path", None):
        os.environ["AUTOREIV_WIKI_PATH"] = args.wiki_path
    return bootstrap_data_dir()


def cmd_status(args: argparse.Namespace) -> int:
    """Prints diagnostic system status to the terminal."""
    paths = apply_storage_args(args)
    hw_calc = HardwareFitCalculator()
    specs = hw_calc.get_hardware_specs()

    store = SQLiteStateStore(db_path=str(paths.db_path))
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)
    registry, _ = BuiltinAgentRegistry.bootstrap(store=store, telemetry=telemetry, wiki_root=str(paths.wiki_path))

    print("\n" + "=" * 60)
    print("   🤖 AutoReiv System Status & Diagnostics")
    print("=" * 60)
    print(f" • Host Platform     : {specs.platform_name} ({specs.cpu_cores} Cores)")
    print(f" • Host RAM          : {specs.total_ram_gb:.1f} GB Total ({specs.available_ram_gb:.1f} GB Available)")
    print(f" • Memory Mode       : {'Unified Memory' if specs.is_unified_memory else 'Standard RAM'}")
    print(f" • Database File     : {paths.db_path} (WAL Mode Active)")
    print(f" • Wiki Root         : {paths.wiki_path}")
    print("-" * 60)
    print(" 📋 Registered Agents:")
    for profile in registry.list_profiles():
        print(
            f"   - {profile.id:<20} | {profile.name:<22} | Tone: {profile.tone.value:<10} | Tools: {len(profile.allowed_tool_names)}"
        )
    print("=" * 60 + "\n")
    return 0


def cmd_routine(args: argparse.Namespace) -> int:
    """Handles routine subcommands."""
    paths = apply_storage_args(args)
    store = SQLiteStateStore(db_path=str(paths.db_path))
    store.initialize_db()

    # Ensure default routines seeded
    for r in BUILTIN_ROUTINES:
        if not store.get_routine(r.id):
            store.save_routine(r)

    if args.routine_command == "list" or not args.routine_command:
        routines = store.list_routines()
        print("\n" + "=" * 70)
        print("   ⏰ AutoReiv Autonomous Routines")
        print("=" * 70)
        print(f" {'ID':<22} | {'Agent':<18} | {'Schedule':<14} | {'Status':<10}")
        print("-" * 70)
        for r in routines:
            sched = r.cron_expression if r.cron_expression else f"{r.interval_seconds}s"
            print(f" {r.id:<22} | {r.agent_id:<18} | {sched:<14} | {r.last_status.value:<10}")
        print("=" * 70 + "\n")
        return 0

    if args.routine_command == "run":
        routine_id = args.routine_id
        routine = store.get_routine(routine_id)
        if not routine:
            print(f"❌ Error: Routine '{routine_id}' not found.", file=sys.stderr)
            return 1

        print(f"▶️  Executing routine '{routine.name}' ({routine.id})...")
        telemetry = TelemetryCollector(store=store)
        registry, tool_reg = BuiltinAgentRegistry.bootstrap(store=store, telemetry=telemetry, wiki_root=str(paths.wiki_path))
        gateway = GatewayProviderFactory.from_env()
        kernel = AgentKernel(gateway=gateway, tool_registry=tool_reg, state_store=store, telemetry=telemetry)
        executor = RoutineExecutor(agent_registry=registry, kernel=kernel, state_store=store, telemetry=telemetry)

        async def run_async():
            return await executor.execute_routine(routine)

        run = asyncio.run(run_async())
        print(f"✅ Routine status: {run.status.value} ({run.duration_ms:.1f} ms)")
        if run.output:
            print(f"\n--- Output ---\n{run.output}\n--------------")
        if run.error_message:
            print(f"\n❌ Error: {run.error_message}", file=sys.stderr)
        return 0

    return 0


def cmd_chat(args: argparse.Namespace) -> int:
    """Interactive terminal chat loop with an agent."""
    paths = apply_storage_args(args)
    store = SQLiteStateStore(db_path=str(paths.db_path))
    store.initialize_db()
    telemetry = TelemetryCollector(store=store)
    registry, tool_reg = BuiltinAgentRegistry.bootstrap(store=store, telemetry=telemetry, wiki_root=str(paths.wiki_path))

    profile = registry.get_profile(args.agent_id)
    if not profile:
        print(f"❌ Error: Agent '{args.agent_id}' not found.", file=sys.stderr)
        return 1

    gateway = GatewayProviderFactory.from_env()
    kernel = AgentKernel(gateway=gateway, tool_registry=tool_reg, state_store=store, telemetry=telemetry)
    sess = store.create_session(agent_id=profile.id, title=f"CLI Chat with {profile.name}")

    print("\n" + "=" * 60)
    print(f"   💬 AutoReiv Interactive Session: {profile.name}")
    print("   Type 'exit' or 'quit' to end session.")
    print("=" * 60 + "\n")

    async def turn_loop():
        while True:
            try:
                user_msg = input("You > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting chat.")
                break

            if not user_msg:
                continue
            if user_msg.lower() in ("exit", "quit", "q"):
                print("Session ended.")
                break

            print(f"\n{profile.name} > ", end="", flush=True)
            async for event in kernel.stream_turn(profile, sess.id, user_msg):
                if event.event_type == KernelEventType.TOKEN and event.content:
                    print(event.content, end="", flush=True)
                elif event.event_type == KernelEventType.TOOL_START and event.tool_call:
                    print(f"\n  [🔧 Invoking tool: {event.tool_call.get('name')}] ", end="", flush=True)
            print("\n")

    asyncio.run(turn_loop())
    return 0


def cmd_backup(args: argparse.Namespace) -> int:
    """Zip the resolved data dir [REQ-DATA-007]."""
    paths = apply_storage_args(args)
    dest = Path(args.dest) if getattr(args, "dest", None) else None
    result = DataDirBackupService(paths).backup(dest)
    print(f"Wrote backup: {result}")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    """Replace the data dir from a zip after --yes [REQ-DATA-008]."""
    paths = apply_storage_args(args)
    if not getattr(args, "yes", False):
        print("Refusing to restore without --yes; live tree unchanged.", file=sys.stderr)
        return 1
    try:
        DataDirBackupService(paths).restore(Path(args.src), confirm=True)
    except DataDirRestoreError as exc:
        print(f"Restore rejected: {exc}", file=sys.stderr)
        return 1
    print(f"Restored data dir: {paths.root}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Launches the FastAPI web server."""
    try:
        import uvicorn
    except ImportError:
        print("❌ Error: 'uvicorn' is not installed. Run 'pip install uvicorn'.", file=sys.stderr)
        return 1

    print(f"🚀 Starting AutoReiv Control Plane on http://{args.host}:{args.port}")
    apply_storage_args(args)

    uvicorn.run(
        "src.web.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI entrypoint."""
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "status":
        return cmd_status(args)
    elif args.command == "routine":
        return cmd_routine(args)
    elif args.command == "chat":
        return cmd_chat(args)
    elif args.command == "backup":
        return cmd_backup(args)
    elif args.command == "restore":
        return cmd_restore(args)
    elif args.command == "serve":
        return cmd_serve(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
