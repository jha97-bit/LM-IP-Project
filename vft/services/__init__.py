"""
VFT Service - Standalone VFT execution and persistence
No dependency on shared MCDA schema
"""
from typing import Optional
from uuid import uuid4
from sqlalchemy.engine import Engine
from persistence.repositories import VftRunRepo, VftDataRepo



class VftService:
    """Service for executing VFT analysis and persisting results."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.run_repo = VftRunRepo(engine)
        self.data_repo = VftDataRepo(engine)

    def execute_vft_run(
        self,
        model,  # VFTModel instance
        executed_by: str = "",
        engine_version: str = "vft=0.1.0"
    ) -> str:
        """
        Execute a VFT run and persist all results to database.
        
        Args:
            model: VFTModel instance with attributes and alternatives
            executed_by: Optional user name/identifier
            engine_version: Version string
        
        Returns:
            run_id: The ID of the created run (UUID string)
        """
        # 1. Create the run record
        run_id = self.run_repo.create_run(
            executed_by=executed_by or "",
            engine_version=engine_version
        )
        
        # 2. Save run configuration
        self.data_repo.save_run_config(
            run_id,
            scaling_type="Linear",
            output_min=0.0,
            output_max=1.0
        )
        
        # 3. Persist criteria (attributes)
        criteria_list = []
        criteria_id_map = {}  # Map attr.id → db criteria_id
        for attr in model.attributes:
            criteria_id = str(uuid4())
            criteria_id_map[attr.id] = criteria_id
            criteria_list.append({
                "criteria_id": criteria_id,
                "name": attr.name,
                "weight": attr.weight,
                "swing_weight": attr.swing_weight,
                "min_val": attr.min_val,
                "max_val": attr.max_val,
                "scaling_direction": attr.scaling_direction,
                "scaling_type": attr.scaling_type,
            })
        returned_criteria_ids = self.data_repo.replace_criteria(run_id, criteria_list)
        # Update map with actual returned IDs (in case they differ)
        for i, attr in enumerate(model.attributes):
            if i < len(returned_criteria_ids):
                criteria_id_map[attr.id] = returned_criteria_ids[i]
        
        # 4. Persist alternatives
        alternatives_list = []
        alt_id_map = {}  # Map alt.id → db alternative_id
        for alt in model.alternatives:
            alt_db_id = str(uuid4())
            alt_id_map[alt.id] = alt_db_id
            alternatives_list.append({
                "alternative_id": alt_db_id,
                "name": alt.name
            })
        returned_alt_ids = self.data_repo.replace_alternatives(run_id, alternatives_list)
        # Update map with actual returned IDs (in case they differ)
        for i, alt in enumerate(model.alternatives):
            if i < len(returned_alt_ids):
                alt_id_map[alt.id] = returned_alt_ids[i]
        
        # 5. Persist raw scores
        raw_scores = []
        for alt in model.alternatives:
            for attr in model.attributes:
                raw_score = alt.get_score(attr.name)
                raw_scores.append({
                    "alternative_id": alt_id_map[alt.id],
                    "criteria_id": criteria_id_map[attr.id],
                    "value": float(raw_score) if raw_score is not None else 0.0
                })
        self.data_repo.replace_raw_scores(run_id, raw_scores)
        
        # 6. Compute and persist criterion utilities
        criterion_utilities = []
        for alt in model.alternatives:
            for attr in model.attributes:
                raw_score = alt.get_score(attr.name)
                utility = attr.get_value(raw_score)  # 0.0-1.0
                criterion_utilities.append({
                    "alternative_id": alt_id_map[alt.id],
                    "criteria_id": criteria_id_map[attr.id],
                    "raw_value": float(raw_score) if raw_score is not None else 0.0,
                    "utility_value": float(utility)
                })
        self.data_repo.replace_criterion_utilities(run_id, criterion_utilities)
        
        # 7. Compute and persist weighted utilities
        weighted_utilities = []
        for alt in model.alternatives:
            for attr in model.attributes:
                raw_score = alt.get_score(attr.name)
                utility = attr.get_value(raw_score)
                weighted_utility = utility * attr.weight
                weighted_utilities.append({
                    "alternative_id": alt_id_map[alt.id],
                    "criteria_id": criteria_id_map[attr.id],
                    "weight": attr.weight,
                    "weighted_utility": float(weighted_utility)
                })
        self.data_repo.replace_weighted_utilities(run_id, weighted_utilities)
        
        # 8. Calculate and persist result scores
        df_scores = model.calculate_scores()
        result_scores = []
        
        # Sort by Total Score descending to assign ranks
        df_sorted = df_scores.sort_values("Total Score", ascending=False).reset_index(drop=True)
        
        for rank, row in df_sorted.iterrows():
            alt_name = row["Alternative"]
            total_score = row["Total Score"]
            
            # Find the alternative to get its ID
            alt = next((a for a in model.alternatives if a.name == alt_name), None)
            if alt:
                result_scores.append({
                    "alternative_id": alt_id_map[alt.id],
                    "total_score": float(total_score),
                    "rank": rank + 1  # 1-indexed
                })
        
        self.data_repo.replace_result_scores(run_id, result_scores)
        
        return run_id

    def list_vft_runs(self, limit: int = 50):
        """List all VFT runs."""
        return self.run_repo.list_runs(limit)
    
    def get_vft_run(self, run_id: str):
        """Get a specific VFT run."""
        return self.run_repo.get_run(run_id)


__all__ = ["VftService"]
