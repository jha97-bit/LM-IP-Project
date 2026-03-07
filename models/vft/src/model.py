import json
import uuid
import pandas as pd
import numpy as np

class Attribute:
    """
    Represents an attribute (objective) in the VFT model.
    """
    def __init__(self, name, min_val=0.0, max_val=100.0, unit="", weight=0.0,
                 scaling_type="Linear", scaling_direction="Increasing", custom_points=None, id=None, swing_weight=50.0):
        """
        Initialize an Attribute.
        """
        self.id = id if id is not None else str(uuid.uuid4())
        self.name = name
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        self.unit = unit
        self.weight = float(weight)
        self.swing_weight = float(swing_weight)
        self.scaling_type = scaling_type
        self.scaling_direction = scaling_direction
        self.custom_points = custom_points if custom_points is not None else []

    def get_value(self, raw_score):
        if self.scaling_type == "Linear":
            return self._linear_scaling(raw_score)
        elif self.scaling_type == "Custom":
            return self._custom_scaling(raw_score)
        return 0.0

    def _linear_scaling(self, x):
        if self.max_val == self.min_val:
            return 0.0

        if self.scaling_direction == "Increasing":
            val = (x - self.min_val) / (self.max_val - self.min_val)
        else: # Decreasing
            val = (self.max_val - x) / (self.max_val - self.min_val)

        return max(0.0, min(1.0, val)) # Clamp between 0 and 1

    def _custom_scaling(self, x):
        if not self.custom_points:
            return 0.0

        # Sort points by x
        points = sorted(self.custom_points, key=lambda p: p[0])
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        return float(np.interp(x, xs, ys))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "unit": self.unit,
            "weight": self.weight,
            "swing_weight": self.swing_weight,
            "scaling_type": self.scaling_type,
            "scaling_direction": self.scaling_direction,
            "custom_points": self.custom_points
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class Alternative:
    """
    Represents an alternative solution in the VFT model.
    """
    def __init__(self, name, scores=None, id=None):
        """
        Initialize an Alternative.
        """
        self.id = id if id is not None else str(uuid.uuid4())
        self.name = name
        self.scores = scores if scores is not None else {}

    def set_score(self, attribute_name, score):
        self.scores[attribute_name] = float(score)

    def get_score(self, attribute_name):
        return self.scores.get(attribute_name, 0.0)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "scores": self.scores
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class VFTModel:
    """
    Main class for the Value-Focused Thinking (VFT) Model.
    Manages attributes and alternatives, and performs calculations.
    """
    def __init__(self):
        self.attributes = []
        self.alternatives = []

    def add_attribute(self, attribute):
        # Check if name exists
        if any(a.name == attribute.name for a in self.attributes):
            raise ValueError(f"Attribute {attribute.name} already exists.")
        self.attributes.append(attribute)

    def remove_attribute(self, name):
        self.attributes = [a for a in self.attributes if a.name != name]
        # Also remove scores from alternatives
        for alt in self.alternatives:
            if name in alt.scores:
                del alt.scores[name]

    def add_alternative(self, alternative):
        if any(a.name == alternative.name for a in self.alternatives):
            raise ValueError(f"Alternative {alternative.name} already exists.")
        self.alternatives.append(alternative)

    def remove_alternative(self, name):
        self.alternatives = [a for a in self.alternatives if a.name != name]

    def update_attribute(self, original_name, new_attribute):
        idx = next((i for i, a in enumerate(self.attributes) if a.name == original_name), -1)
        if idx != -1:
            self.attributes[idx] = new_attribute
            # Update alternative keys if name changed
            if original_name != new_attribute.name:
                for alt in self.alternatives:
                    if original_name in alt.scores:
                        alt.scores[new_attribute.name] = alt.scores.pop(original_name)

    def update_alternative(self, original_name, new_alternative):
        idx = next((i for i, a in enumerate(self.alternatives) if a.name == original_name), -1)
        if idx != -1:
            self.alternatives[idx] = new_alternative

    def calculate_scores(self):
        data = []
        for alt in self.alternatives:
            row = {"Alternative": alt.name, "Total Score": 0.0}
            weighted_sum = 0.0
            for attr in self.attributes:
                raw = alt.get_score(attr.name)
                val = attr.get_value(raw)
                w_score = val * attr.weight
                weighted_sum += w_score

                # row[f"{attr.name} (Raw)"] = raw
                # row[f"{attr.name} (Value)"] = val
                row[f"{attr.name} (Weighted)"] = w_score

            row["Total Score"] = weighted_sum
            data.append(row)

        return pd.DataFrame(data)

    def to_json(self):
        return json.dumps({
            "attributes": [a.to_dict() for a in self.attributes],
            "alternatives": [a.to_dict() for a in self.alternatives]
        }, indent=4)

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        model = cls()
        for attr_data in data["attributes"]:
            model.add_attribute(Attribute.from_dict(attr_data))
        for alt_data in data["alternatives"]:
            model.add_alternative(Alternative.from_dict(alt_data))
        return model
