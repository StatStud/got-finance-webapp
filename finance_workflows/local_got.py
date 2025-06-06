"""
Local Graph of Thoughts implementation
Extracted from the main GoT repository to avoid OpenAI import issues
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union, Callable, Iterator
import itertools
import logging
import json

class AbstractLanguageModel(ABC):
    """Abstract base class that defines the interface for all language models."""

    def __init__(self, config_path: str = "", model_name: str = "", cache: bool = False):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = None
        self.model_name = model_name
        self.cache = cache
        if self.cache:
            self.response_cache = {}
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost = 0.0

    def load_config(self, path: str) -> None:
        """Load configuration from a specified path."""
        if path == "":
            return
        
        try:
            with open(path, "r") as f:
                self.config = json.load(f)
            self.logger.debug(f"Loaded config from {path} for {self.model_name}")
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {path}")
            self.config = {}

    def clear_cache(self) -> None:
        """Clear the response cache."""
        if hasattr(self, 'response_cache'):
            self.response_cache.clear()

    @abstractmethod
    def query(self, query: str, num_responses: int = 1) -> Any:
        """Abstract method to query the language model."""
        pass

    @abstractmethod
    def get_response_texts(self, query_responses: Union[List[Any], Any]) -> List[str]:
        """Abstract method to extract response texts from the language model's response(s)."""
        pass

class Thought:
    """Represents an LLM thought with its state and various flags."""
    _ids: Iterator[int] = itertools.count(0)

    def __init__(self, state: Dict = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.id = next(Thought._ids)
        self.state = state or {}
        self._score = 0.0
        self._valid = False
        self._solved = False
        self.scored = False
        self.validated = False
        self.compared_to_ground_truth = False

    @staticmethod
    def from_thought(thought):
        """Creates a new thought from an existing one."""
        new_thought = Thought(thought.state)
        new_thought.score = thought.score
        new_thought.valid = thought.valid
        new_thought.solved = thought.solved
        new_thought.scored = thought.scored
        new_thought.validated = thought.validated
        new_thought.compared_to_ground_truth = thought.compared_to_ground_truth
        return new_thought

    @property
    def valid(self):
        return self._valid

    @valid.setter
    def valid(self, valid):
        self.validated = True
        self._valid = valid

    @property
    def score(self):
        return self._score

    @score.setter
    def score(self, new_score):
        self.scored = True
        self._score = new_score

    @property
    def solved(self):
        return self._solved

    @solved.setter
    def solved(self, solved):
        self.compared_to_ground_truth = True
        self._solved = solved


class Operation(ABC):
    """Abstract base class for all operations."""
    _ids: Iterator[int] = itertools.count(0)

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.id = next(Operation._ids)
        self.predecessors = []
        self.successors = []
        self.executed = False

    def can_be_executed(self):
        return all(predecessor.executed for predecessor in self.predecessors)

    def get_previous_thoughts(self):
        previous_thoughts = [
            thought
            for predecessor in self.predecessors
            for thought in predecessor.get_thoughts()
        ]
        return previous_thoughts

    def add_predecessor(self, operation):
        self.predecessors.append(operation)
        operation.successors.append(self)

    def add_successor(self, operation):
        self.successors.append(operation)
        operation.predecessors.append(self)

    def execute(self, lm, prompter, parser, **kwargs):
        assert self.can_be_executed(), "Not all predecessors have been executed"
        self.logger.info(f"Executing operation {self.id}")
        self._execute(lm, prompter, parser, **kwargs)
        self.executed = True

    @abstractmethod
    def _execute(self, lm, prompter, parser, **kwargs):
        pass

    @abstractmethod
    def get_thoughts(self):
        pass


class Generate(Operation):
    """Operation to generate thoughts."""
    def __init__(self, num_branches_prompt=1, num_branches_response=1):
        super().__init__()
        self.num_branches_prompt = num_branches_prompt
        self.num_branches_response = num_branches_response
        self.thoughts = []

    def get_thoughts(self):
        return self.thoughts

    def _execute(self, lm, prompter, parser, **kwargs):
        previous_thoughts = self.get_previous_thoughts()

        if len(previous_thoughts) == 0 and len(self.predecessors) > 0:
            return

        if len(previous_thoughts) == 0:
            previous_thoughts = [Thought(state=kwargs)]

        for thought in previous_thoughts:
            base_state = thought.state
            prompt = prompter.generate_prompt(self.num_branches_prompt, **base_state)
            self.logger.debug(f"Prompt for LM: {prompt}")
            
            responses = lm.get_response_texts(
                lm.query(prompt, num_responses=self.num_branches_response)
            )
            self.logger.debug(f"Responses from LM: {responses}")
            
            for new_state in parser.parse_generate_answer(base_state, responses):
                new_state = {**base_state, **new_state}
                self.thoughts.append(Thought(new_state))

        self.logger.info(f"Generate operation {self.id} created {len(self.thoughts)} new thoughts")


class Score(Operation):
    """Operation to score thoughts."""
    def __init__(self, num_samples=1, combined_scoring=False, scoring_function=None):
        super().__init__()
        self.num_samples = num_samples
        self.combined_scoring = combined_scoring
        self.thoughts = []
        self.scoring_function = scoring_function

    def get_thoughts(self):
        return self.thoughts

    def _execute(self, lm, prompter, parser, **kwargs):
        previous_thoughts = self.get_previous_thoughts()
        assert len(self.predecessors) > 0, "Score operation needs at least one predecessor"

        if self.combined_scoring:
            previous_thoughts_states = [thought.state for thought in previous_thoughts]
            if self.scoring_function is not None:
                scores = self.scoring_function(previous_thoughts_states)
            else:
                prompt = prompter.score_prompt(previous_thoughts_states)
                responses = lm.get_response_texts(
                    lm.query(prompt, num_responses=self.num_samples)
                )
                scores = parser.parse_score_answer(previous_thoughts_states, responses)
            
            for thought, score in zip(previous_thoughts, scores):
                new_thought = Thought.from_thought(thought)
                new_thought.score = score
                self.thoughts.append(new_thought)
        else:
            for thought in previous_thoughts:
                new_thought = Thought.from_thought(thought)
                if self.scoring_function is not None:
                    score = self.scoring_function(thought.state)
                else:
                    prompt = prompter.score_prompt([thought.state])
                    responses = lm.get_response_texts(
                        lm.query(prompt, num_responses=self.num_samples)
                    )
                    score = parser.parse_score_answer([thought.state], responses)[0]

                new_thought.score = score
                self.thoughts.append(new_thought)

        self.logger.info(f"Score operation {self.id} scored {len(self.thoughts)} thoughts")


class KeepBestN(Operation):
    """Keep the best N thoughts from predecessors based on their score."""
    def __init__(self, n, higher_is_better=True):
        super().__init__()
        self.n = n
        assert self.n > 0, "KeepBestN operation must keep at least one thought"
        self.higher_is_better = higher_is_better
        self.thoughts = []

    def get_best_n(self):
        previous_thoughts = self.get_previous_thoughts()
        assert all(
            previous_thought.scored for previous_thought in previous_thoughts
        ), "Not all thoughts have been scored"

        return sorted(
            previous_thoughts,
            key=lambda thought: thought.score,
            reverse=self.higher_is_better,
        )[: self.n]

    def get_thoughts(self):
        return self.thoughts

    def _execute(self, lm, prompter, parser, **kwargs):
        assert len(self.predecessors) >= 1, "KeepBestN operation must have at least one predecessor"
        self.thoughts = [Thought.from_thought(thought) for thought in self.get_best_n()]
        self.logger.info(f"KeepBestN operation {self.id} kept {len(self.thoughts)} thoughts")


class Aggregate(Operation):
    """Operation to aggregate thoughts."""
    def __init__(self, num_responses=1):
        super().__init__()
        self.thoughts = []
        self.num_responses = num_responses

    def get_thoughts(self):
        return self.thoughts

    def _execute(self, lm, prompter, parser, **kwargs):
        assert len(self.predecessors) >= 1, "Aggregate operation must have at least one predecessor"
        previous_thoughts = self.get_previous_thoughts()

        if len(previous_thoughts) == 0:
            return

        base_state = {}
        for thought in sorted(previous_thoughts, key=lambda thought: thought.score):
            base_state = {**base_state, **thought.state}

        previous_thought_states = [thought.state for thought in previous_thoughts]
        prompt = prompter.aggregation_prompt(previous_thought_states)

        responses = lm.get_response_texts(
            lm.query(prompt, num_responses=self.num_responses)
        )

        parsed = parser.parse_aggregation_answer(previous_thought_states, responses)

        if isinstance(parsed, dict):
            parsed = [parsed]
        for new_state in parsed:
            self.thoughts.append(Thought({**base_state, **new_state}))


class GroundTruth(Operation):
    """Operation to evaluate if thoughts correctly solve the problem."""
    def __init__(self, ground_truth_evaluator):
        super().__init__()
        self.ground_truth_evaluator = ground_truth_evaluator
        self.thoughts = []

    def get_thoughts(self):
        return self.thoughts

    def _execute(self, lm, prompter, parser, **kwargs):
        assert len(self.predecessors) >= 1, "GroundTruth operation must have at least one predecessor"
        previous_thoughts = self.get_previous_thoughts()

        for thought in previous_thoughts:
            new_thought = Thought.from_thought(thought)
            try:
                new_thought.solved = self.ground_truth_evaluator(new_thought.state)
            except:
                new_thought.solved = False
            self.thoughts.append(new_thought)

        self.logger.info(
            f"GroundTruth operation {self.id} evaluated {len(self.thoughts)} thoughts and "
            f"{len([thought for thought in self.thoughts if thought.solved])} solved the problem"
        )


class GraphOfOperations:
    """Represents the Graph of Operations."""
    def __init__(self):
        self.operations = []
        self.roots = []
        self.leaves = []

    def append_operation(self, operation):
        self.operations.append(operation)

        if len(self.roots) == 0:
            self.roots = [operation]
        else:
            for leave in self.leaves:
                leave.add_successor(operation)

        self.leaves = [operation]

    def add_operation(self, operation):
        self.operations.append(operation)
        if len(self.roots) == 0:
            self.roots = [operation]
            self.leaves = [operation]
            assert len(operation.predecessors) == 0, "First operation should have no predecessors"
        else:
            if len(operation.predecessors) == 0:
                self.roots.append(operation)
            for predecessor in operation.predecessors:
                if predecessor in self.leaves:
                    self.leaves.remove(predecessor)
            if len(operation.successors) == 0:
                self.leaves.append(operation)


class Controller:
    """Controller class to manage the execution flow of the Graph of Operations."""
    def __init__(self, lm, graph, prompter, parser, problem_parameters):
        self.logger = logging.getLogger(self.__class__.__module__)
        self.lm = lm
        self.graph = graph
        self.prompter = prompter
        self.parser = parser
        self.problem_parameters = problem_parameters
        self.run_executed = False

    def run(self):
        self.logger.debug("Checking that the program is in a valid state")
        assert self.graph.roots is not None, "The operations graph has no root"
        self.logger.debug("The program is in a valid state")

        execution_queue = [
            operation
            for operation in self.graph.operations
            if operation.can_be_executed()
        ]

        while len(execution_queue) > 0:
            current_operation = execution_queue.pop(0)
            self.logger.info(f"Executing operation {current_operation.__class__.__name__}")
            current_operation.execute(
                self.lm, self.prompter, self.parser, **self.problem_parameters
            )
            for operation in current_operation.successors:
                assert (
                    operation in self.graph.operations
                ), "The successor of an operation is not in the operations graph"
                if operation.can_be_executed():
                    execution_queue.append(operation)
        self.logger.info("All operations executed")
        self.run_executed = True

    def get_final_thoughts(self):
        assert self.run_executed, "The run method has not been executed"
        return [operation.get_thoughts() for operation in self.graph.leaves]

    def output_graph(self, path):
        """Serialize the state and results of the operations graph to a JSON file."""
        output = []
        for operation in self.graph.operations:
            operation_serialized = {
                "operation": operation.__class__.__name__,
                "thoughts": [thought.state for thought in operation.get_thoughts()],
            }
            if any([thought.scored for thought in operation.get_thoughts()]):
                operation_serialized["scored"] = [
                    thought.scored for thought in operation.get_thoughts()
                ]
                operation_serialized["scores"] = [
                    thought.score for thought in operation.get_thoughts()
                ]
            if any([thought.validated for thought in operation.get_thoughts()]):
                operation_serialized["validated"] = [
                    thought.validated for thought in operation.get_thoughts()
                ]
                operation_serialized["validity"] = [
                    thought.valid for thought in operation.get_thoughts()
                ]
            output.append(operation_serialized)

        output.append(
            {
                "prompt_tokens": getattr(self.lm, 'prompt_tokens', 0),
                "completion_tokens": getattr(self.lm, 'completion_tokens', 0),
                "cost": getattr(self.lm, 'cost', 0.0),
            }
        )

        with open(path, "w") as file:
            file.write(json.dumps(output, indent=2))

class ValidateAndImprove(Operation):
    """Operation to validate and improve thoughts."""
    def __init__(self, num_samples=1, improve=True, num_tries=3, validate_function=None):
        super().__init__()
        self.num_samples = num_samples
        self.improve = improve
        self.num_tries = num_tries
        self.validate_function = validate_function
        self.thoughts = []

    def get_thoughts(self):
        return [thought_list[-1] for thought_list in self.thoughts]

    def _execute(self, lm, prompter, parser, **kwargs):
        previous_thoughts = self.get_previous_thoughts()
        assert len(self.predecessors) > 0, "ValidateAndImprove operation needs at least one predecessor"

        for thought in previous_thoughts:
            thought_list = []
            current_thought = Thought.from_thought(thought)
            current_try = 0
            
            while True:
                if self.validate_function is not None:
                    valid = self.validate_function(current_thought.state)
                else:
                    # Simple validation - assume valid for now
                    valid = True
                
                current_thought.valid = valid
                thought_list.append(current_thought)
                
                if not self.improve or current_thought.valid or current_try >= self.num_tries:
                    break
                    
                # Try to improve
                current_try += 1
                # For simplicity, just copy the thought for now
                current_thought = Thought.from_thought(current_thought)
            
            self.thoughts.append(thought_list)

class Improve(Operation):
    """Operation to improve thoughts."""
    def __init__(self):
        super().__init__()
        self.thoughts = []

    def get_thoughts(self):
        return self.thoughts

    def _execute(self, lm, prompter, parser, **kwargs):
        previous_thoughts = self.get_previous_thoughts()
        assert len(self.predecessors) > 0, "Improve operation needs at least one predecessor"

        for thought in previous_thoughts:
            # For now, just copy the thought - you can add actual improvement logic
            improved_thought = Thought.from_thought(thought)
            self.thoughts.append(improved_thought)

class KeepValid(Operation):
    """Operation to keep valid thoughts."""
    def __init__(self):
        super().__init__()
        self.thoughts = []

    def get_thoughts(self):
        return self.thoughts

    def _execute(self, lm, prompter, parser, **kwargs):
        previous_thoughts = self.get_previous_thoughts()
        assert len(self.predecessors) >= 1, "KeepValid operation must have at least one predecessor"

        self.thoughts = [
            Thought.from_thought(thought)
            for thought in previous_thoughts
            if not thought.validated or thought.valid
        ]

class Selector(Operation):
    """Operation to select thoughts using a custom selector function."""
    def __init__(self, selector):
        super().__init__()
        self.selector = selector
        self.thoughts = []

    def get_thoughts(self):
        return self.thoughts

    def _execute(self, lm, prompter, parser, **kwargs):
        previous_thoughts = self.get_previous_thoughts()
        
        if len(previous_thoughts) == 0:
            previous_thoughts = [Thought(kwargs)]

        selected_thoughts = self.selector(previous_thoughts)
        self.thoughts = [Thought.from_thought(thought) for thought in selected_thoughts]


# Create convenience modules for easy import
class Operations:
    GraphOfOperations = GraphOfOperations
    Generate = Generate
    Score = Score
    KeepBestN = KeepBestN
    Aggregate = Aggregate
    GroundTruth = GroundTruth
    ValidateAndImprove = ValidateAndImprove
    Improve = Improve
    KeepValid = KeepValid
    Selector = Selector
    Thought = Thought
    AbstractLanguageModel = AbstractLanguageModel

class ControllerModule:
    Controller = Controller

# Create instances
operations = Operations()
controller = ControllerModule()