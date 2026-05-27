"""
BatteryFold CLI — command-line interface for the Aphrodite-builder platform.

Commands:
    setup       Configure environment (AI, dependencies)
    screen      Run molecular screening pipeline
    ladder      Run multi-precision escalation
    analyze     Run battery metrics analysis
    adapt       Evaluate molecules for planetary environments
    monitor     View pipeline status and monitoring dashboard
    version     Show version info
"""
import argparse
import json
import sys
from pathlib import Path


def cmd_setup(args):
    """Run setup wizard."""
    if args.ai:
        from ..ai_interface import AIInterface
        AIInterface.interactive_setup()
    elif args.check:
        import subprocess
        setup_script = Path(__file__).parent.parent.parent / 'scripts' / 'setup.sh'
        if setup_script.exists():
            subprocess.run(['bash', str(setup_script)])
        else:
            print("Setup script not found. Run: bash scripts/setup.sh")
    else:
        print("Usage: batteryfold setup --ai | --check")
        print("  --ai     Configure AI provider (Claude/GLM/DeepSeek)")
        print("  --check  Check dependency installation status")


def cmd_screen(args):
    """Run molecular screening pipeline."""
    from ..workflows.screening_pipeline import ScreeningPipeline

    molecules = {}
    if args.smiles:
        for i, smi in enumerate(args.smiles):
            molecules[f"mol_{i}"] = smi
    elif args.file:
        with open(args.file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(None, 1)
                if len(parts) == 2:
                    molecules[parts[0]] = parts[1]
                else:
                    molecules[f"mol_{len(molecules)}"] = parts[0]

    if not molecules:
        print("Error: provide --smiles or --file with molecule list")
        sys.exit(1)

    pipeline = ScreeningPipeline(
        workdir=args.workdir or './screening_run',
        method=args.method or 'r2SCAN-3c',
        solvent=args.solvent or 'CPCM(water)',
    )

    print(f"Screening {len(molecules)} molecules...")
    results = pipeline.run(molecules=molecules)
    report = pipeline.generate_report(results)
    print(report)


def cmd_ladder(args):
    """Run multi-precision escalation pipeline."""
    from ..workflows.precision_ladder import PrecisionLadder

    molecules = {}
    if args.file:
        with open(args.file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split(None, 1)
                if len(parts) == 2:
                    molecules[parts[0]] = parts[1]

    if not molecules:
        print("Error: provide --file with {name} {xyz_content} entries")
        sys.exit(1)

    ladder = PrecisionLadder(workdir=args.workdir or './precision_run')
    results = ladder.escalate(molecules, target_tier=args.tier or 'dlpno')
    print(f"Escalation complete. {sum(1 for v in results.values() if v and v[-1].passed)} molecules passed all tiers.")


def cmd_analyze(args):
    """Run battery metrics analysis."""
    from ..workflows.battery_analysis import BatteryAnalysisWorkflow, AnalysisType

    workflow = BatteryAnalysisWorkflow(
        workdir=args.workdir or './analysis',
        method=args.method or 'r2SCAN-3c',
    )

    if not args.name or not args.xyz:
        print("Error: provide --name and --xyz")
        sys.exit(1)

    with open(args.xyz) as f:
        xyz_content = f.read()

    atype = AnalysisType(args.type) if args.type else AnalysisType.FULL
    reports = workflow.run(args.name, xyz_content, atype)

    for report in reports:
        print(f"\n[{report.analysis_type}] {report.molecule_name}")
        print(f"  Method: {report.method}")
        for note in report.notes:
            print(f"  - {note}")


def cmd_adapt(args):
    """Evaluate molecules for planetary environments."""
    from ..workflows.planetary_adapter import PlanetaryAdapter, Environment

    adapter = PlanetaryAdapter()
    envs = [Environment(e) for e in (args.environments or ['venus', 'mars', 'orbital'])]

    if args.file:
        with open(args.file) as f:
            molecules = json.load(f)
    else:
        print("Error: provide --file with molecule properties JSON")
        sys.exit(1)

    results = adapter.batch_evaluate(molecules, envs)
    report = adapter.generate_report(results)
    print(report)


def cmd_monitor(args):
    """Show pipeline monitoring dashboard."""
    from ..monitoring.dashboard import print_dashboard
    print_dashboard(args.workdir or '.')


def cmd_version(args):
    """Show version info."""
    print("BatteryFold v1.0.0")
    print("Part of Aphrodite-builder — First-principles molecular design platform")
    print("https://github.com/doublelw/Aphrodite-builder2")


def main():
    parser = argparse.ArgumentParser(
        prog='batteryfold',
        description='BatteryFold — Organic battery molecular design CLI',
    )
    subparsers = parser.add_subparsers(dest='command')

    # setup
    p_setup = subparsers.add_parser('setup', help='Configure environment')
    p_setup.add_argument('--ai', action='store_true', help='Configure AI provider')
    p_setup.add_argument('--check', action='store_true', help='Check dependencies')

    # screen
    p_screen = subparsers.add_parser('screen', help='Run molecular screening')
    p_screen.add_argument('--smiles', nargs='+', help='SMILES strings')
    p_screen.add_argument('--file', help='File with name SMILES pairs')
    p_screen.add_argument('--method', default='r2SCAN-3c')
    p_screen.add_argument('--solvent', default='CPCM(water)')
    p_screen.add_argument('--workdir', default='./screening_run')

    # ladder
    p_ladder = subparsers.add_parser('ladder', help='Multi-precision escalation')
    p_ladder.add_argument('--file', required=True, help='XYZ molecules file')
    p_ladder.add_argument('--tier', default='dlpno', choices=['xtb', 'dft', 'dlpno'])
    p_ladder.add_argument('--workdir', default='./precision_run')

    # analyze
    p_analyze = subparsers.add_parser('analyze', help='Battery metrics analysis')
    p_analyze.add_argument('--name', help='Molecule name')
    p_analyze.add_argument('--xyz', help='XYZ geometry file')
    p_analyze.add_argument('--type', choices=['redox', 'reorganization', 'thermal', 'flame', 'cycle', 'solvent', 'full'])
    p_analyze.add_argument('--method', default='r2SCAN-3c')
    p_analyze.add_argument('--workdir', default='./analysis')

    # adapt
    p_adapt = subparsers.add_parser('adapt', help='Planetary environment evaluation')
    p_adapt.add_argument('--file', required=True, help='Molecule properties JSON')
    p_adapt.add_argument('--environments', nargs='+', default=['venus', 'mars', 'orbital'])
    p_adapt.add_argument('--workdir', default='./adaptation')

    # monitor
    p_monitor = subparsers.add_parser('monitor', help='Pipeline monitoring')
    p_monitor.add_argument('--workdir', default='.')

    # version
    subparsers.add_parser('version', help='Show version')

    args = parser.parse_args()

    commands = {
        'setup': cmd_setup,
        'screen': cmd_screen,
        'ladder': cmd_ladder,
        'analyze': cmd_analyze,
        'adapt': cmd_adapt,
        'monitor': cmd_monitor,
        'version': cmd_version,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
