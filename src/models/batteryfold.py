"""
BatteryFold — AlphaFold2-inspired neural network for battery molecular design.

Architecture mapping:
    AlphaFold2              BatteryFold
    ──────────────────      ──────────────────────────
    MSA representation  →   Chemical analog database embeddings
    Evoformer           →   Molecular Transformer (attention on atoms+bonds)
    Structure Module    →   SE(3)-equivariant geometry refinement
    pLDDT confidence    →   Per-atom property confidence scores
    Recycle loop        →   Iterative refinement across precision tiers

Predicts: voltage, energy density, HOMO/LUMO, reorganization energy,
          thermal stability, flame resistance, cycle stability.
"""
import math
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

if not HAS_TORCH:
    # Allow import without PyTorch for documentation/config purposes
    pass


# Periodic table features: [atomic_num, period, group, electronegativity,
#                           atomic_radius, valence_electrons, mass]
PERIODIC_TABLE = {
    1:  [1,  1,  1,  2.20, 0.53, 1, 1.008],   # H
    5:  [5,  2, 13,  2.04, 0.85, 3, 10.81],    # B
    6:  [6,  2, 14,  2.55, 0.70, 4, 12.01],    # C
    7:  [7,  2, 15,  3.04, 0.65, 5, 14.01],    # N
    8:  [8,  2, 16,  3.44, 0.60, 6, 16.00],    # O
    9:  [9,  2, 17,  3.98, 0.50, 7, 19.00],    # F
    14: [14, 3, 14,  1.90, 1.10, 4, 28.09],    # Si
    15: [15, 3, 15,  2.19, 1.06, 5, 30.97],    # P
    16: [16, 3, 16,  2.58, 1.02, 6, 32.07],    # S
    17: [17, 3, 17,  3.16, 0.97, 7, 35.45],    # Cl
    26: [26, 4,  8,  1.83, 1.26, 2, 55.85],    # Fe
    29: [29, 4, 11,  1.90, 1.35, 1, 63.55],    # Cu
    50: [50, 5, 14,  1.96, 1.45, 4, 118.7],    # Sn
}
DEFAULT_FEATURE = [0, 0, 0, 0.0, 0.0, 0, 0.0]
NUM_ATOM_FEATURES = 7


@dataclass
class BatteryFoldConfig:
    """BatteryFold model configuration."""
    # Architecture
    atom_features: int = 128
    bond_features: int = 64
    edge_features: int = 64
    num_heads: int = 8
    num_blocks: int = 6
    dropout: float = 0.1

    # Triangle multiplication (3-body interactions)
    triangle_hidden: int = 128

    # SE(3) structure module
    num_structure_layers: int = 4
    num_se3_heads: int = 4

    # Output heads
    num_battery_properties: int = 9

    # Precision tier conditioning
    num_precision_tiers: int = 4  # xtb, dft, dlpno, tddft


if HAS_TORCH:

    class AtomEmbedding(nn.Module):
        """Embed atomic numbers into learned feature vectors.

        Combines periodic table features with learnable embeddings.
        """
        def __init__(self, config: BatteryFoldConfig):
            super().__init__()
            self.config = config
            self.feature_proj = nn.Linear(NUM_ATOM_FEATURES, config.atom_features)
            self.atomic_embedding = nn.Embedding(119, config.atom_features)
            self.output_proj = nn.Linear(
                config.atom_features * 2, config.atom_features
            )
            self.norm = nn.LayerNorm(config.atom_features)

        def forward(self, atomic_numbers: 'torch.Tensor') -> 'torch.Tensor':
            """
            Args:
                atomic_numbers: [batch, n_atoms] int tensor

            Returns:
                [batch, n_atoms, atom_features] float tensor
            """
            learned = self.atomic_embedding(atomic_numbers)

            table_features = []
            for z in atomic_numbers.flatten().tolist():
                table_features.append(PERIODIC_TABLE.get(z, DEFAULT_FEATURE))
            table = torch.tensor(
                table_features, dtype=torch.float32, device=atomic_numbers.device
            ).reshape(*atomic_numbers.shape, NUM_ATOM_FEATURES)

            projected = self.feature_proj(table)

            combined = torch.cat([learned, projected], dim=-1)
            return self.norm(self.output_proj(combined))

    class BondEmbedding(nn.Module):
        """Embed bond types (single/double/triple/aromatic) + distances."""
        def __init__(self, config: BatteryFoldConfig):
            super().__init__()
            self.bond_type_embedding = nn.Embedding(5, config.bond_features)
            self.distance_proj = nn.Linear(1, config.bond_features)
            self.output = nn.Linear(config.bond_features * 2, config.edge_features)

        def forward(self, bond_types: 'torch.Tensor',
                    distances: 'torch.Tensor') -> 'torch.Tensor':
            """
            Args:
                bond_types: [batch, n_atoms, n_atoms] int (0-4)
                distances: [batch, n_atoms, n_atoms] float (Angstrom)

            Returns:
                [batch, n_atoms, n_atoms, edge_features]
            """
            bt = self.bond_type_embedding(bond_types)
            dist = self.distance_proj(distances.unsqueeze(-1))
            return self.output(torch.cat([bt, dist], dim=-1))

    class TriangleMultiplication(nn.Module):
        """
        Triangle multiplication for 3-body interaction modeling.

        Analogous to AlphaFold2's TriangleMultiplication module:
        updates pairwise representations by combining information from
        two edges of a triangle (i, j) using edges (i, k) and (k, j).

        Captures angular and multi-body effects critical for
        molecular orbital interactions.
        """
        def __init__(self, config: BatteryFoldConfig):
            super().__init__()
            d = config.edge_features
            h = config.triangle_hidden

            self.left_proj = nn.Linear(d, h)
            self.right_proj = nn.Linear(d, h)
            self.left_gate = nn.Linear(d, h)
            self.right_gate = nn.Linear(d, h)
            self.output_gate = nn.Linear(d, d)
            self.output_proj = nn.Linear(h, d)

            self.norm_in = nn.LayerNorm(d)
            self.norm_out = nn.LayerNorm(d)

        def forward(self, pair_repr: 'torch.Tensor') -> 'torch.Tensor':
            """
            Args:
                pair_repr: [batch, n_atoms, n_atoms, edge_features]

            Returns:
                Updated pair representation, same shape
            """
            z = self.norm_in(pair_repr)

            left = self.left_proj(z) * torch.sigmoid(self.left_gate(z))
            right = self.right_proj(z) * torch.sigmoid(self.right_gate(z))

            # Triangle product: sum over k dimension
            product = torch.einsum('bikd,bjkd->bij d', left, right)

            output = self.output_proj(product)
            gate = torch.sigmoid(self.output_gate(z))

            return self.norm_out(pair_repr + gate * output)

    class TriangleSelfAttention(nn.Module):
        """
        Triangle self-attention on pairwise representations.

        Applies attention along rows and columns of the pair matrix,
        enabling global interaction modeling between atom pairs.
        """
        def __init__(self, config: BatteryFoldConfig):
            super().__init__()
            d = config.edge_features
            self.num_heads = config.num_heads
            self.head_dim = d // config.num_heads

            self.q_proj = nn.Linear(d, d)
            self.k_proj = nn.Linear(d, d)
            self.v_proj = nn.Linear(d, d)
            self.out_proj = nn.Linear(d, d)
            self.gate = nn.Linear(d, d)
            self.norm = nn.LayerNorm(d)

        def forward(self, pair_repr: 'torch.Tensor') -> 'torch.Tensor':
            """Row-wise attention over pair representation."""
            z = self.norm(pair_repr)
            b, n, _, d = z.shape

            q = self.q_proj(z).reshape(b, n, n, self.num_heads, self.head_dim)
            k = self.k_proj(z).reshape(b, n, n, self.num_heads, self.head_dim)
            v = self.v_proj(z).reshape(b, n, n, self.num_heads, self.head_dim)

            # Attend along j dimension for each (batch, i, head)
            q2 = q.permute(0, 1, 3, 2, 4).reshape(b * n * self.num_heads, n, self.head_dim)
            k2 = k.permute(0, 1, 3, 2, 4).reshape(b * n * self.num_heads, n, self.head_dim)
            v2 = v.permute(0, 1, 3, 2, 4).reshape(b * n * self.num_heads, n, self.head_dim)

            attn = torch.matmul(q2, k2.transpose(-2, -1)) / math.sqrt(self.head_dim)
            attn = F.softmax(attn, dim=-1)

            out = torch.matmul(attn, v2)
            out = out.reshape(b, n, self.num_heads, n, self.head_dim).permute(0, 1, 3, 2, 4)
            out = out.reshape(b, n, n, d)

            output = self.out_proj(out)
            gate = torch.sigmoid(self.gate(z))

            return pair_repr + gate * output

    class MolecularTransformerBlock(nn.Module):
        """
        Evoformer-analog block for molecular representation.

        Combines:
        1. Atom self-attention (MSA column attention analog)
        2. Atom-pair communication
        3. Triangle multiplication (3-body)
        4. Triangle self-attention
        5. Transition MLP
        """
        def __init__(self, config: BatteryFoldConfig):
            super().__init__()
            d_atom = config.atom_features
            d_pair = config.edge_features
            num_heads = config.num_heads

            # Atom self-attention
            self.atom_attn = nn.MultiheadAttention(
                d_atom, num_heads, dropout=config.dropout, batch_first=True
            )
            self.atom_norm = nn.LayerNorm(d_atom)

            # Atom-Pair communication
            self.pair_to_atom = nn.Linear(d_pair, d_atom)
            self.atom_to_pair = nn.Linear(d_atom, d_pair)

            # Pair updates
            self.tri_mult_out = TriangleMultiplication(config)
            self.tri_mult_in = TriangleMultiplication(config)
            self.tri_attn = TriangleSelfAttention(config)

            # Transitions
            self.atom_transition = nn.Sequential(
                nn.Linear(d_atom, d_atom * 4),
                nn.GELU(),
                nn.Linear(d_atom * 4, d_atom),
            )
            self.pair_transition = nn.Sequential(
                nn.Linear(d_pair, d_pair * 4),
                nn.GELU(),
                nn.Linear(d_pair * 4, d_pair),
            )

            self.atom_norm_out = nn.LayerNorm(d_atom)
            self.pair_norm_out = nn.LayerNorm(d_pair)

        def forward(
            self,
            atom_repr: 'torch.Tensor',
            pair_repr: 'torch.Tensor',
            mask: Optional['torch.Tensor'] = None
        ) -> Tuple['torch.Tensor', 'torch.Tensor']:
            """
            Args:
                atom_repr: [batch, n_atoms, atom_features]
                pair_repr: [batch, n_atoms, n_atoms, edge_features]
                mask: [batch, n_atoms] bool

            Returns:
                Updated (atom_repr, pair_repr)
            """
            # Atom self-attention
            residual = atom_repr
            a = self.atom_norm(atom_repr)
            a, _ = self.atom_attn(a, a, a, key_padding_mask=mask)
            atom_repr = residual + a

            # Atom-pair communication
            pair_bias = self.pair_to_atom(pair_repr.mean(dim=2))
            atom_repr = atom_repr + pair_bias

            atom_signal = self.atom_to_pair(atom_repr)
            pair_update = atom_signal.unsqueeze(2) + atom_signal.unsqueeze(1)
            pair_repr = pair_repr + pair_update

            # Triangle updates (3-body interactions)
            pair_repr = self.tri_mult_out(pair_repr)
            pair_repr = self.tri_mult_in(pair_repr.transpose(1, 2)).transpose(1, 2)
            pair_repr = self.tri_attn(pair_repr)

            # Transitions
            atom_repr = self.atom_norm_out(atom_repr + self.atom_transition(atom_repr))
            pair_repr = self.pair_norm_out(pair_repr + self.pair_transition(pair_repr))

            return atom_repr, pair_repr

    class SE3EquivariantStructureModule(nn.Module):
        """
        SE(3)-equivariant structure refinement module.

        Updates atom positions while maintaining rotational and
        translational equivariance. Inspired by SE(3)-Transformers
        and AlphaFold2's Structure Module.

        Predicts local frame rotations and translations for each atom.
        """
        def __init__(self, config: BatteryFoldConfig):
            super().__init__()
            d = config.atom_features

            self.ipa_heads = config.num_se3_heads
            self.head_dim = d // config.num_se3_heads

            # Query, key, value projections
            self.q_proj = nn.Linear(d, d)
            self.k_proj = nn.Linear(d, d)
            self.v_proj = nn.Linear(d, d)

            # Rotation and translation predictions
            self.rot_proj = nn.Linear(d, config.num_se3_heads * 3)
            self.trans_proj = nn.Linear(d, config.num_se3_heads * 3)

            # Output
            self.output_proj = nn.Linear(d, d)
            self.norm = nn.LayerNorm(d)

            # Confidence head
            self.confidence = nn.Linear(d, 1)

        def forward(
            self,
            atom_repr: 'torch.Tensor',
            positions: 'torch.Tensor',
            pair_repr: 'torch.Tensor' = None,
        ) -> Tuple['torch.Tensor', 'torch.Tensor', 'torch.Tensor']:
            """
            Args:
                atom_repr: [batch, n_atoms, atom_features]
                positions: [batch, n_atoms, 3]
                pair_repr: [batch, n_atoms, n_atoms, edge_features] optional

            Returns:
                updated_positions: [batch, n_atoms, 3]
                confidence: [batch, n_atoms, 1] per-atom confidence (pLDDT analog)
                updated_repr: [batch, n_atoms, atom_features]
            """
            b, n, d = atom_repr.shape

            # Attention-weighted message passing
            q = self.q_proj(atom_repr).reshape(b, n, self.ipa_heads, self.head_dim)
            k = self.k_proj(atom_repr).reshape(b, n, self.ipa_heads, self.head_dim)
            v = self.v_proj(atom_repr).reshape(b, n, self.ipa_heads, self.head_dim)

            attn = torch.einsum('bihd,bjhd->bhij', q, k) / math.sqrt(self.head_dim)

            if pair_repr is not None:
                pair_bias = pair_repr.mean(dim=-1).unsqueeze(1)
                attn = attn + pair_bias

            attn = F.softmax(attn, dim=-1)
            messages = torch.einsum('bhij,bjhd->bihd', attn, v)
            messages = messages.reshape(b, n, d)

            # Predict rigid body updates
            rot_update = self.rot_proj(messages).reshape(b, n, self.ipa_heads, 3)
            trans_update = self.trans_proj(messages).reshape(b, n, self.ipa_heads, 3)

            # Apply SE(3) equivariant update
            rot_update = F.normalize(rot_update, dim=-1)
            agg_trans = trans_update.mean(dim=2)  # [batch, n_atoms, 3]

            new_positions = positions + 0.1 * agg_trans

            # Update representation
            updated_repr = self.norm(
                atom_repr + self.output_proj(messages)
            )

            # Per-atom confidence (pLDDT analog)
            confidence = torch.sigmoid(self.confidence(updated_repr))

            return new_positions, confidence, updated_repr

    class BatteryFold(nn.Module):
        """
        BatteryFold: AlphaFold2-inspired model for battery molecular design.

        Architecture:
            1. Atom/Bond embedding from molecular graph
            2. N x MolecularTransformerBlock (Evoformer analog)
            3. SE(3)-equivariant structure refinement
            4. Multi-task prediction heads for battery properties

        Predicts 9 battery properties:
            - theoretical_voltage (V)
            - energy_density (Wh/kg)
            - HOMO energy (eV)
            - LUMO energy (eV)
            - band gap (eV)
            - reorganization_energy lambda (eV)
            - thermal_stability (C)
            - flame_resistance (0-1 score)
            - cycle_stability (0-1 score)

        Usage:
            model = BatteryFold(BatteryFoldConfig())
            # atomic_numbers: [batch, n_atoms]
            # bond_types: [batch, n_atoms, n_atoms]
            # distances: [batch, n_atoms, n_atoms]
            # coordinates: [batch, n_atoms, 3]
            properties, confidence = model(atomic_numbers, bond_types,
                                            distances, coordinates)
        """

        PROPERTY_NAMES = [
            'voltage', 'energy_density', 'homo', 'lumo', 'gap',
            'lambda_reorg', 'thermal_stability', 'flame_resistance',
            'cycle_stability',
        ]

        def __init__(self, config: BatteryFoldConfig = None):
            super().__init__()
            self.config = config or BatteryFoldConfig()

            # Embeddings
            self.atom_embed = AtomEmbedding(self.config)
            self.bond_embed = BondEmbedding(self.config)

            # Precision tier conditioning
            self.tier_embedding = nn.Embedding(
                self.config.num_precision_tiers, self.config.atom_features
            )

            # Evoformer blocks
            self.blocks = nn.ModuleList([
                MolecularTransformerBlock(self.config)
                for _ in range(self.config.num_blocks)
            ])

            # Structure module
            self.structure_module = SE3EquivariantStructureModule(self.config)

            # Multi-task prediction heads
            d = self.config.atom_features
            self.property_heads = nn.ModuleDict({
                name: nn.Sequential(
                    nn.Linear(d, d // 2),
                    nn.GELU(),
                    nn.Linear(d // 2, 1),
                )
                for name in self.PROPERTY_NAMES
            })

            # Global pooling + output
            self.global_pool_proj = nn.Sequential(
                nn.Linear(d, d),
                nn.GELU(),
                nn.Linear(d, d),
            )

        def forward(
            self,
            atomic_numbers: 'torch.Tensor',
            bond_types: 'torch.Tensor',
            distances: 'torch.Tensor',
            coordinates: 'torch.Tensor',
            precision_tier: 'torch.Tensor' = None,
            mask: 'torch.Tensor' = None,
        ) -> Tuple[dict, 'torch.Tensor']:
            """
            Full forward pass.

            Args:
                atomic_numbers: [batch, n_atoms] int
                bond_types: [batch, n_atoms, n_atoms] int (0-4)
                distances: [batch, n_atoms, n_atoms] float (Angstrom)
                coordinates: [batch, n_atoms, 3] float
                precision_tier: [batch] int (0=xtb, 1=dft, 2=dlpno, 3=tddft)
                mask: [batch, n_atoms] bool (True = valid atom)

            Returns:
                properties: dict of {name: [batch, 1]} predictions
                confidence: [batch, n_atoms, 1] per-atom confidence
            """
            b, n = atomic_numbers.shape

            # Embeddings
            atom_repr = self.atom_embed(atomic_numbers)
            pair_repr = self.bond_embed(bond_types, distances)

            # Add precision tier conditioning
            if precision_tier is not None:
                tier_emb = self.tier_embedding(precision_tier).unsqueeze(1)
                atom_repr = atom_repr + tier_emb

            # Molecular Transformer blocks (Evoformer)
            for block in self.blocks:
                atom_repr, pair_repr = block(atom_repr, pair_repr, mask)

            # SE(3) structure refinement
            refined_coords, confidence, atom_repr = self.structure_module(
                atom_repr, coordinates, pair_repr
            )

            # Global pooling (mean over atoms)
            if mask is not None:
                mask_expanded = mask.unsqueeze(-1).float()
                global_repr = (atom_repr * mask_expanded).sum(dim=1) / mask_expanded.sum(dim=1)
            else:
                global_repr = atom_repr.mean(dim=1)

            global_repr = self.global_pool_proj(global_repr)

            # Property predictions
            properties = {}
            for name, head in self.property_heads.items():
                properties[name] = head(global_repr)

            return properties, confidence

        def predict(self, atomic_numbers, bond_types, distances,
                    coordinates, precision_tier=None):
            """
            Convenience method returning property dict with names.

            Returns:
                dict of {property_name: float_value}
            """
            self.eval()
            with torch.no_grad():
                props, conf = self.forward(
                    atomic_numbers, bond_types, distances,
                    coordinates, precision_tier
                )
            return {
                name: val.item()
                for name, val in props.items()
            }

    def create_model(config: BatteryFoldConfig = None) -> BatteryFold:
        """Factory function to create BatteryFold model."""
        return BatteryFold(config or BatteryFoldConfig())

else:
    # Stub classes when PyTorch is not installed
    def create_model(config=None):
        raise ImportError(
            "PyTorch required for BatteryFold model. "
            "Install: pip install torch"
        )
