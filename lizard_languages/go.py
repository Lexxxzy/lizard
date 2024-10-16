'''
Language parser for Go lang
'''

from .code_reader import CodeReader, CodeStateMachine
from .clike import CCppCommentsMixin
from .golike import GoLikeStates


class GoReader(CodeReader, CCppCommentsMixin):
    # pylint: disable=R0903

    ext = ['go']
    language_names = ['go']

    def __init__(self, context):
        super(GoReader, self).__init__(context)
        self.parallel_states = [GoStates(context)]


'''
Language parser for Go lang
'''

from .golike import GoLikeStates


class GoStates(GoLikeStates):
    """
    State machine for parsing Go language specifics.
    """

    def __init__(self, context):
        super(GoStates, self).__init__(context)
        self._collected_tokens = []
        self._possible_function_name = None

    def _state_global(self, token):
        """
        Global state handling, overridden for Go-specific parsing.
        """
        if token == self.FUNC_KEYWORD:
            self._state = self._after_func
        elif token == 'type':
            self._state = self._type_definition
        elif token == '{':
            self.sub_state(self.statemachine_clone())
        elif token == '}':
            self.statemachine_return()
        else:
            super(GoStates, self)._state_global(token)

    def _after_func(self, token):
        """
        Handle tokens after 'func' keyword.
        """
        if token == '(':
            # Possible method with receiver or anonymous function with parameters
            self._collected_tokens = []
            self._state = self._collect_receiver_or_parameters
        elif token not in ('{', '(', ''):
            # Function name
            self.context.push_new_function(token)
            self.context.current_function.long_name = token
            self._state = self._expect_function_dec
        else:
            # Anonymous function without parameters
            self.context.push_new_function('(anonymous)')
            self.context.current_function.long_name = '(anonymous)'
            self._state = self._after_parameters
            self.next(self._after_parameters, token)

    def _collect_receiver_or_parameters(self, token):
        """
        Collect tokens inside parentheses after 'func'.
        """
        if token == ')':
            self._state = self._after_receiver_or_parameters
        else:
            # Collect tokens inside parentheses
            self._collected_tokens.append(token)

    def _after_receiver_or_parameters(self, token):
        """
        Handle tokens after receiver or parameters.
        """
        if token != '`':
            if token not in ('{', '(', ')', self.FUNC_KEYWORD):
                self._possible_function_name = token
                self._state = self._check_for_parameters
            else:
                # Anonymous function
                self.context.push_new_function('(anonymous)')
                params = ' '.join(self._collected_tokens).strip()
                if params:
                    self.context.parameter(params)
                self._state = self._after_parameters
                self.next(self._after_parameters, token)

    def _check_for_parameters(self, token):
        """
        Check for function parameters after possible function name.
        """
        if token == '(':
            self.context.push_new_function(self._possible_function_name)
            receiver = ' '.join(self._collected_tokens).strip()
            if receiver != '':
                long_name = f'({receiver}){self._possible_function_name}'
            else:
                long_name = self._possible_function_name
            self.context.current_function.long_name = long_name
            self._state = self._function_dec
            self.next(self._function_dec, token)
        else:
            # Not a function name, treat as anonymous function
            self.context.push_new_function('(anonymous)')
            self.context.current_function.long_name = '(anonymous)'
            params = ''.join(self._collected_tokens).strip()
            if params:
                self.context.parameter(params)
            self._collected_tokens = []
            self._state = self._after_parameters
            self.next(self._after_parameters, token)

    def _expect_function_dec(self, token):
        """
        Expect function declaration parameters.
        """
        if token == '(':
            self.next(self._function_dec, token)
        else:
            # Proceed to read return type or function body
            self._state = self._after_parameters
            self.next(self._after_parameters, token)

    @CodeStateMachine.read_inside_brackets_then("()", '_after_parameters')
    def _function_dec(self, token):
        """
        Handle function parameter parsing.
        """
        if token not in '()':
            self.context.parameter(token)

    def _after_parameters(self, token):
        """
        Handle tokens after function parameters.
        """
        if token == '<':
            # Handle type parameters (generics)
            self._state = self._read_type_parameters
        elif token == '(':
            # Handle multiple return types
            self._state = self._multi_return_type
            self.next(self._multi_return_type, token)
        elif token == '{':
            self._state = self._function_impl
            self.next(self._function_impl, token)
        elif token != '':
            self._state = self._read_return_type
            self.next(self._read_return_type, token)
        else:
            # No return type, expect function body
            self._state = self._expect_function_impl

    @CodeStateMachine.read_inside_brackets_then("<>", '_after_parameters')
    def _read_type_parameters(self, tokens):
        """
        Handle generic type parameters.
        """
        pass  # Consume type parameters for generics

    @CodeStateMachine.read_inside_brackets_then("()", '_expect_function_impl')
    def _multi_return_type(self, tokens):
        """
        Handle multiple return types.
        """
        pass  # Consume multiple return types

    def _read_return_type(self, token):
        """
        Read function return type.
        """
        if token == '{':
            self.next(self._function_impl, token)
        elif token == '(':
            self._state = self._multi_return_type
            self.next(self._multi_return_type, token)
        elif token == 'interface':
            self._state = self._interface_return_type
        elif token == 'func':
            self._state = self._function_type
        elif token == '[':
            self._state = self._array_return_type
            self.next(self._array_return_type, token)
        else:
            # Continue reading return type
            self._state = self._read_return_type

    @CodeStateMachine.read_inside_brackets_then("{}", '_expect_function_impl')
    def _interface_return_type(self, tokens):
        """
        Handle 'interface{}' as return type.
        """
        pass  # Consume 'interface{}' as return type

    @CodeStateMachine.read_inside_brackets_then("()", '_expect_function_impl')
    def _function_type(self, tokens):
        """
        Handle 'func()' as return type.
        """
        pass  # Consume 'func()' as return type

    @CodeStateMachine.read_inside_brackets_then("[]", '_read_return_type')
    def _array_return_type(self, tokens):
        """
        Handle array return types.
        """
        pass  # Handle array return types

    def _expect_function_impl(self, token):
        """
        Expect function implementation.
        """
        if token == "interface":
            self._state = self._interface_return_type
        elif token == '{':
            self.next(self._function_impl, token)
        else:
            # Skip tokens until function body starts
            self._state = self._expect_function_impl

    def _function_impl(self, _):
        """
        Handle function implementation.
        """
        def callback():
            self.context.end_of_function()
            self._state = self._state_global
        self.sub_state(self.statemachine_clone(), callback)
