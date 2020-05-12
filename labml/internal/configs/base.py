from typing import Dict, List, Callable, Union, Tuple

from labml.internal import util

from .config_function import ConfigFunction
from .config_item import ConfigItem
from .parser import Parser, PropertyKeys


def _is_class_method(func: Callable):
    if not callable(func):
        return False

    import inspect

    spec: inspect.Signature = inspect.signature(func)
    params: List[inspect.Parameter] = list(spec.parameters.values())
    if len(params) != 1:
        return False
    p = params[0]
    if p.kind != p.POSITIONAL_OR_KEYWORD:
        return False

    return p.name == 'self'


class Configs:
    r"""
    You should sub-class this class to create your own configurations
    """

    _calculators: Dict[str, List[ConfigFunction]] = {}
    _evaluators: Dict[str, List[ConfigFunction]] = {}

    def __init_subclass__(cls, **kwargs):
        configs = {}

        for k, v in cls.__annotations__.items():
            if not Parser.is_valid(k):
                continue

            configs[k] = ConfigItem(k,
                                    True, v,
                                    k in cls.__dict__, cls.__dict__.get(k, None))

        evals = []
        for k, v in cls.__dict__.items():
            if not Parser.is_valid(k):
                continue

            if _is_class_method(v):
                evals.append((k, v))
                continue

            configs[k] = ConfigItem(k,
                                    k in cls.__annotations__, cls.__annotations__.get(k, None),
                                    True, v)

        for e in evals:
            cls._add_eval_function(e[1], e[0], 'default')

        for k, v in configs.items():
            setattr(cls, k, v)

    @classmethod
    def _add_config_function(cls,
                             func: Callable,
                             name: Union[ConfigItem, List[ConfigItem]],
                             option: str, *,
                             is_append: bool
                             ):
        if PropertyKeys.calculators not in cls.__dict__:
            cls._calculators = {}

        calc = ConfigFunction(func, config_names=name, option_name=option, is_append=is_append)
        if type(calc.config_names) == str:
            config_names = [calc.config_names]
        else:
            config_names = calc.config_names

        for n in config_names:
            if n not in cls._calculators:
                cls._calculators[n] = []
            cls._calculators[n].append(calc)

    @classmethod
    def _add_eval_function(cls,
                           func: Callable,
                           name: str,
                           option: str):
        if PropertyKeys.evaluators not in cls.__dict__:
            cls._evaluators = {}

        calc = ConfigFunction(func,
                              config_names=name,
                              option_name=option,
                              is_append=False,
                              check_string_names=False)

        if name not in cls._evaluators:
            cls._evaluators[name] = []
        cls._evaluators[name].append(calc)

    @classmethod
    def calc(cls, name: Union[ConfigItem, List[ConfigItem]] = None,
             option: str = None, *,
             is_append: bool = False):
        r"""
        Use this as a decorator to register configuration options.

        Arguments:
            name: the configuration item or a list of items.
                If it is a list of items the function should return
                tuple.
            option (str, optional): name of the option.
                If not provided it will be derived from the
                function name.
        """

        def wrapper(func: Callable):
            cls._add_config_function(func, name, option, is_append=is_append)

            return func

        return wrapper

    @classmethod
    def list(cls, name: str = None):
        return cls.calc(name, f"_{util.random_string()}", is_append=True)

    @classmethod
    def set_hyperparams(cls, *args: ConfigItem, is_hyperparam=True):
        r"""
        Identifies configuration as (or not) hyper-parameters

        Arguments:
            *args: list of configurations
            is_hyperparam (bool, optional): whether the provided configuration
                items are hyper-parameters. Defaults to ``True``.
        """
        if PropertyKeys.hyperparams not in cls.__dict__:
            cls._hyperparams = {}

        for h in args:
            cls._hyperparams[h.key] = is_hyperparam

    @classmethod
    def aggregate(cls, name: Union[ConfigItem, any], option: str,
                  *args: Tuple[Union[ConfigItem, any], str]):
        r"""
        Aggregate configs

        Arguments:
            name: name of the aggregate
            option: aggregate option
            *args: list of options
        """

        assert args

        if PropertyKeys.aggregates not in cls.__dict__:
            cls._aggregates = {}

        if name.key not in cls._aggregates:
            cls._aggregates[name.key] = {}

        pairs = {p[0].key: p[1] for p in args}
        cls._aggregates[name.key][option] = pairs
