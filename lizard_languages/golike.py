'''
Language parser base for Go-like languages
'''

from .code_reader import CodeStateMachine


class GoLikeStates(CodeStateMachine):
    """
    Base state machine for languages similar to Go.
    """

    FUNC_KEYWORD = 'func'

    def _state_global(self, token):
        """
        Global state handling.
        """
        if token == self.FUNC_KEYWORD:
            self._state = self._function_name
            self.context.push_new_function('')
        elif token == 'type':
            self._state = self._type_definition
        elif token == '{':
            self.sub_state(self.statemachine_clone())
        elif token == '}':
            self.statemachine_return()

    def _type_definition(self, token):
        """
        Handle type definitions.
        """
        self._state = self._after_type_name

    def _after_type_name(self, token):
        """
        Handle tokens after a type name.
        """
        if token == 'struct':
            self._state = self._struct_definition
        elif token == 'interface':
            self._state = self._interface_definition
        else:
            self._state = self._state_global

    @CodeStateMachine.read_inside_brackets_then("{}", "_state_global")
    def _struct_definition(self, tokens):
        """
        Read struct definition.
        """
        pass

    @CodeStateMachine.read_inside_brackets_then("{}", "_state_global")
    def _interface_definition(self, tokens):
        """
        Read interface definition.
        """
        pass

    def _function_name(self, token):
        """
        Handle function name parsing.
        """
        if token != '`':
            if token == '(':
                if (len(self.context.stacked_functions) > 0 and
                        self.context.stacked_functions[-1].name != '*global*'):
                    return self.next(self._function_dec, token)
                else:
                    return self.next(self._member_function, token)
            if token == '{':
                return self.next(self._expect_function_impl, token)
            self.context.add_to_function_name(token)
            self._state = self._expect_function_dec

    def _expect_function_dec(self, token):
        """
        Expect function declaration parameters.
        """
        if token == '(':
            self.next(self._function_dec, token)
        elif token == "<":
            self.next(self._generalize, token)
        else:
            self._state = self._state_global

    @CodeStateMachine.read_inside_brackets_then("<>", "_expect_function_dec")
    def _generalize(self, tokens):
        """
        Handle generic type parameters.
        """
        pass

    @CodeStateMachine.read_inside_brackets_then("()", '_function_name')
    def _member_function(self, tokens):
        """
        Handle member function parsing.
        """
        self.context.add_to_long_function_name(tokens)

    @CodeStateMachine.read_inside_brackets_then("()", '_expect_function_impl')
    def _function_dec(self, token):
        """
        Handle function parameter parsing.
        """
        if token not in '()':
            self.context.parameter(token)

    def _expect_function_impl(self, token):
        """
        Expect function implementation.
        """
        if token == '{' and self.last_token != 'interface':
            self.next(self._function_impl, token)

    def _function_impl(self, _):
        """
        Handle function implementation.
        """
        def callback():
            self._state = self._state_global
            self.context.end_of_function()
        self.sub_state(self.statemachine_clone(), callback)
