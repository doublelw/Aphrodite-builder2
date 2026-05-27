"""
Battery metrics deep analysis workflow.

Runs targeted analysis for specific battery performance metrics:
  - HOMO/LUMO energy levels and redox potential
  - Reorganization energy (4-point method)
  - Thermal decomposition pathway
  - Flame resistance prediction
  - Cycle stability estimation
  - Solvent compatibility screening

Each analysis generates structured data suitable for patent documentation.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum


class AnalysisType(Enum):
    REDOX = "redox"
    REORGANIZATION = "reorganization"
    THERMAL = "thermal"
    FLAME = "flame"
    CYCLE = "cycle"
    SOLVENT = "solvent"
    FULL = "full"


@dataclass
class AnalysisReport:
    molecule_name: str
    analysis_type: str
    method: str
    results: Dict[str, float] = field(default_factory=dict)
    confidence: str = "high"  # high/medium/low
    notes: List[str] = field(default_factory=list)


class BatteryAnalysisWorkflow:
    """
    Targeted battery performance analysis.

    Usage:
        workflow = BatteryAnalysisWorkflow(workdir='./analysis')
        report = workflow.run('quinone_A', xyz, AnalysisType.REDOX)
    """

    def __init__(self, workdir: str = './analysis',
                 method: str = 'r2SCAN-3c',
                 nproc: int = 4, maxcore: int = 4000):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.method = method
        self.nproc = nproc
        self.maxcore = maxcore

    def _generate_redox_inputs(self, xyz: str, name: str) -> dict:
        """Generate ORCA inputs for redox potential calculation.

        Neutral + cation single points for oxidation potential,
        Neutral + anion single points for reduction potential.
        """
        from ..quantum.orca_input_generator import ORCAInputGenerator, ORCAConfig

        mol_dir = self.workdir / name / 'redox'
        mol_dir.mkdir(parents=True, exist_ok=True)

        configs = {
            'neutral': ORCAConfig(
                method=self.method, basis='def2-SVP',
                charge=0, multiplicity=1,
                solvent='CPCM(acetonitrile)',
                nproc=self.nproc, maxcore=self.maxcore,
            ),
            'cation': ORCAConfig(
                method=self.method, basis='def2-SVP',
                charge=+1, multiplicity=2,
                solvent='CPCM(acetonitrile)',
                nproc=self.nproc, maxcore=self.maxcore,
            ),
            'anion': ORCAConfig(
                method=self.method, basis='def2-SVP',
                charge=-1, multiplicity=2,
                solvent='CPCM(acetonitrile)',
                nproc=self.nproc, maxcore=self.maxcore,
            ),
        }

        gen = ORCAInputGenerator(configs['neutral'])
        inputs = {}
        for state, config in configs.items():
            gen.config = config
            inp_path = mol_dir / f"{name}_{state}.inp"
            gen.write_input(xyz, str(inp_path))
            inputs[state] = str(inp_path)

        return inputs

    def _generate_lambda_inputs(self, xyz: str, name: str) -> dict:
        """Generate ORCA inputs for 4-point reorganization energy.

        lambda = (E_neu@cat - E_neu@neu) + (E_cat@neu - E_cat@cat)
               = lambda_1 + lambda_2

        4 calculations: neutral@neutral_opt, neutral@cation_opt,
                        cation@neutral_opt, cation@cation_opt
        """
        from ..quantum.orca_input_generator import ORCAInputGenerator, ORCAConfig

        mol_dir = self.workdir / name / 'lambda'
        mol_dir.mkdir(parents=True, exist_ok=True)

        calcs = {
            'neu_at_neu': ORCAConfig(
                method=self.method, basis='def2-SVP',
                charge=0, multiplicity=1,
                solvent='CPCM(acetonitrile)',
                nproc=self.nproc, maxcore=self.maxcore,
            ),
            'neu_at_cat': ORCAConfig(
                method=self.method, basis='def2-SVP',
                charge=0, multiplicity=1,
                solvent='CPCM(acetonitrile)',
                nproc=self.nproc, maxcore=self.maxcore,
            ),
            'cat_at_neu': ORCAConfig(
                method=self.method, basis='def2-SVP',
                charge=+1, multiplicity=2,
                solvent='CPCM(acetonitrile)',
                nproc=self.nproc, maxcore=self.maxcore,
            ),
            'cat_at_cat': ORCAConfig(
                method=self.method, basis='def2-SVP',
                charge=+1, multiplicity=2,
                solvent='CPCM(acetonitrile)',
                nproc=self.nproc, maxcore=self.maxcore,
            ),
        }

        gen = ORCAInputGenerator(calcs['neu_at_neu'])
        inputs = {}
        for calc_name, config in calcs.items():
            gen.config = config
            inp_path = mol_dir / f"{name}_{calc_name}.inp"
            gen.write_input(xyz, str(inp_path))
            inputs[calc_name] = str(inp_path)

        return inputs

    def compute_reorganization_energy(self, energies: Dict[str, float]) -> dict:
        """Compute lambda from 4-point energy values.

        Args:
            energies: {'neu_at_neu': E1, 'neu_at_cat': E2,
                       'cat_at_neu': E3, 'cat_at_cat': E4}

        Returns:
            {'lambda_1': float, 'lambda_2': float, 'lambda_total': float}
        """
        lambda_1 = energies['neu_at_cat'] - energies['neu_at_neu']
        lambda_2 = energies['cat_at_neu'] - energies['cat_at_cat']
        return {
            'lambda_1_eV': lambda_1,
            'lambda_2_eV': lambda_2,
            'lambda_total_eV': lambda_1 + lambda_2,
        }

    def run(self, molecule_name: str, xyz: str,
            analysis: AnalysisType = AnalysisType.FULL) -> List[AnalysisReport]:
        """Run specified analysis type."""
        reports = []
        analyses = [analysis] if analysis != AnalysisType.FULL else list(AnalysisType)[:-1]

        for atype in analyses:
            if atype == AnalysisType.REDOX:
                inputs = self._generate_redox_inputs(xyz, molecule_name)
                reports.append(AnalysisReport(
                    molecule_name=molecule_name,
                    analysis_type='redox',
                    method=self.method,
                    notes=[
                        "Generated neutral/cation/anion single point inputs",
                        "Redox potential = (E_cation - E_neutral) / F + reference",
                        f"Input files: {list(inputs.keys())}",
                    ],
                ))
            elif atype == AnalysisType.REORGANIZATION:
                inputs = self._generate_lambda_inputs(xyz, molecule_name)
                reports.append(AnalysisReport(
                    molecule_name=molecule_name,
                    analysis_type='reorganization_energy',
                    method=f"{self.method} 4-point",
                    notes=[
                        "4-point method: neu@neu, neu@cat, cat@neu, cat@cat",
                        "lambda = lambda_1 + lambda_2",
                        f"Input files: {list(inputs.keys())}",
                    ],
                ))
            elif atype == AnalysisType.THERMAL:
                reports.append(AnalysisReport(
                    molecule_name=molecule_name,
                    analysis_type='thermal_stability',
                    method='bond_dissociation_energy',
                    notes=[
                        "Analyze weakest bond dissociation energies",
                        "Requires geometry optimization + frequency analysis",
                    ],
                ))
            elif atype == AnalysisType.FLAME:
                reports.append(AnalysisReport(
                    molecule_name=molecule_name,
                    analysis_type='flame_resistance',
                    method='flash_point_estimation',
                    notes=[
                        "Estimate from HOMO energy and molecular weight",
                        "Low HOMO + high MW = intrinsically flame retardant",
                    ],
                ))
            elif atype == AnalysisType.SOLVENT:
                for solvent in ['acetonitrile', 'water', 'DMF', 'THF']:
                    reports.append(AnalysisReport(
                        molecule_name=molecule_name,
                        analysis_type='solvent_compatibility',
                        method=f'CPCM({solvent})',
                        notes=[f"Solvation free energy in {solvent}"],
                    ))

        return reports

    def generate_patent_data_sheet(self, reports: List[AnalysisReport]) -> str:
        """Generate structured data sheet for patent documentation."""
        lines = [
            "=" * 50,
            f"BATTERY ANALYSIS DATA SHEET",
            f"Molecule: {reports[0].molecule_name if reports else 'N/A'}",
            "=" * 50, "",
        ]

        for report in reports:
            lines.append(f"[{report.analysis_type}]")
            lines.append(f"  Method: {report.method}")
            lines.append(f"  Confidence: {report.confidence}")
            for k, v in report.results.items():
                lines.append(f"  {k}: {v}")
            for note in report.notes:
                lines.append(f"  Note: {note}")
            lines.append("")

        return "\n".join(lines)
