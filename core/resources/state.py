from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, Set, Optional
from core.common.models import ResourceState, Span, ResourceSymbol


@dataclass
class AbstractStore:
    """Abstract Store tracking symbol bindings and resource states along CFG paths."""
    symbol_to_id: Dict[str, str] = field(default_factory=dict)
    id_to_state: Dict[str, ResourceState] = field(default_factory=dict)
    id_to_symbol: Dict[str, ResourceSymbol] = field(default_factory=dict)
    aliases: Dict[str, Set[str]] = field(default_factory=dict)  # ResID -> Set of variable names

    def clone(self) -> 'AbstractStore':
        return AbstractStore(
            symbol_to_id=deepcopy(self.symbol_to_id),
            id_to_state=deepcopy(self.id_to_state),
            id_to_symbol=deepcopy(self.id_to_symbol),
            aliases=deepcopy(self.aliases),
        )

    def register_resource(self, var_name: str, symbol: ResourceSymbol) -> None:
        res_id = symbol.id
        self.symbol_to_id[var_name] = res_id
        self.id_to_state[res_id] = ResourceState.OPEN_MUST_CLOSE
        self.id_to_symbol[res_id] = symbol
        if res_id not in self.aliases:
            self.aliases[res_id] = set()
        self.aliases[res_id].add(var_name)

    def set_state(self, var_name_or_id: str, new_state: ResourceState) -> bool:
        res_id = self.symbol_to_id.get(var_name_or_id, var_name_or_id)
        if res_id in self.id_to_state:
            self.id_to_state[res_id] = new_state
            return True
        return False

    def get_state(self, var_name_or_id: str) -> ResourceState:
        res_id = self.symbol_to_id.get(var_name_or_id, var_name_or_id)
        return self.id_to_state.get(res_id, ResourceState.UNACQUIRED)

    def add_alias(self, alias_var: str, original_var: str) -> None:
        res_id = self.symbol_to_id.get(original_var)
        if res_id:
            self.symbol_to_id[alias_var] = res_id
            self.aliases[res_id].add(alias_var)

    @staticmethod
    def join_states(s1: ResourceState, s2: ResourceState) -> ResourceState:
        if s1 == s2:
            return s1
        if s1 == ResourceState.UNKNOWN or s2 == ResourceState.UNKNOWN:
            return ResourceState.UNKNOWN
        if (s1 == ResourceState.OPEN_MUST_CLOSE and s2 == ResourceState.CLOSED) or \
           (s1 == ResourceState.CLOSED and s2 == ResourceState.OPEN_MUST_CLOSE):
            return ResourceState.MAYBE_LEAKED
        if s1 == ResourceState.MAYBE_LEAKED or s2 == ResourceState.MAYBE_LEAKED:
            return ResourceState.MAYBE_LEAKED
        if s1 == ResourceState.TRANSFERRED or s2 == ResourceState.TRANSFERRED:
            return ResourceState.TRANSFERRED
        return ResourceState.MAYBE_LEAKED

    def join(self, other: 'AbstractStore') -> 'AbstractStore':
        merged = self.clone()
        all_ids = set(self.id_to_state.keys()) | set(other.id_to_state.keys())

        for res_id in all_ids:
            state1 = self.id_to_state.get(res_id, ResourceState.UNACQUIRED)
            state2 = other.id_to_state.get(res_id, ResourceState.UNACQUIRED)
            merged.id_to_state[res_id] = self.join_states(state1, state2)

            if res_id not in merged.id_to_symbol and res_id in other.id_to_symbol:
                merged.id_to_symbol[res_id] = other.id_to_symbol[res_id]

        return merged
