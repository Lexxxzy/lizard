'''
Language parser for JavaScript
'''

from .clike import CLikeReader, CLikeStates


class JavaReader(CLikeReader):
    # pylint: disable=R0903

    ext = ['java']
    language_names = ['java']

    def __init__(self, context):
        super(JavaReader, self).__init__(context)
        self.parallel_states = [JavaStates(context)]


class JavaStates(CLikeStates):  # pylint: disable=R0903
    def _state_old_c_params(self, token):
        if token == '{':
            self._state_dec_to_imp(token)

    def _state_global(self, token):
        if token == '@':
            self._state = self._state_decorator
            return
        super(JavaStates, self)._state_global(token)

    def _state_decorator(self, _):
        self._state = self._state_post_decorator

    def _state_post_decorator(self, token):
        if token == '.':
            self._state = self._state_decorator
        else:
            self._state = self._state_global
            self._state(token)
