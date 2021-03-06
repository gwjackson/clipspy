# Copyright (c) 2016-2017, Matteo Cafasso
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
# OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import clips

from clips.facts import Facts
from clips.agenda import Agenda
from clips.classes import Classes
from clips.modules import Modules
from clips.functions import Functions
from clips.error import CLIPSError, ErrorRouter
from clips.common import CLIPSType, EnvData, ENVIRONMENT_DATA

from clips._clips import lib, ffi


class Environment(object):
    """The environment class encapsulates an independent CLIPS engine
    with its own data structures.

    All the CLIPS APIs are accessible through the Environment and grouped
    into the following namespaces.

    * Facts: facts and templates
    * Agenda: rules and activations
    * Classes: classes and instances
    * Modules: modules and global variables
    * Functions: functions, generics and methods

    """

    __slots__ = ('_env', '_facts', '_agenda',
                 '_classes', '_modules', '_functions')

    def __init__(self):
        self._env = lib.CreateEnvironment()
        self._facts = Facts(self._env)
        self._agenda = Agenda(self._env)
        self._classes = Classes(self._env)
        self._modules = Modules(self._env)
        self._functions = Functions(self._env)

        lib.define_function(self._env)

        error_router = ErrorRouter('python-error-router', 40)
        error_router.add_to_environment(self)

        ENVIRONMENT_DATA[self._env] = EnvData({}, error_router)

    def __del__(self):
        try:
            lib.DestroyEnvironment(self._env)
            del ENVIRONMENT_DATA[self._env]
        except (AttributeError, KeyError, TypeError):
            pass  # mostly happening during interpreter shutdown

    @property
    def facts(self):
        """Environment Facts namespace.

        Fact and Template functions are grouped under this namespace.

        """
        return self._facts

    @property
    def agenda(self):
        """Environment Agenda namespace.

        The Agenda and the Rule functions are grouped under this namespace.

        """
        return self._agenda

    @property
    def classes(self):
        """Environment Classes namespace.

        Class and Instance functions are grouped under this namespace.

        """
        return self._classes

    @property
    def modules(self):
        """Environment Modules namespace.

        Module and Global functions are grouped under this namespace.

        """
        return self._modules

    @property
    def functions(self):
        """Environment Functions namespace.

        Function and Generic functions are grouped under this namespace.

        """
        return self._functions

    def load(self, path):
        """Load a set of constructs into the CLIPS data base.

        The Python equivalent of the CLIPS load command.

        """
        ret = lib.EnvBload(self._env, path.encode())
        if ret != 1:
            ret = lib.EnvLoad(self._env, path.encode())
            if ret != 1:
                raise CLIPSError(self._env)

    def save(self, path, binary=False):
        """Save a set of constructs into the CLIPS data base.

        If binary is True, the constructs will be saved in binary format.

        The Python equivalent of the CLIPS load command.

        """
        if binary:
            ret = lib.EnvBsave(self._env, path.encode())
        else:
            ret = lib.EnvSave(self._env, path.encode())
        if ret == 0:
            raise CLIPSError(self._env)

    def batch_star(self, path):
        """Evaluate the commands contained in the specific path.

        The Python equivalent of the CLIPS batch* command.

        """
        if lib.EnvBatchStar(self._env, path.encode()) != 1:
            raise CLIPSError(self._env)

    def build(self, construct):
        """Build a single construct in CLIPS.

        The Python equivalent of the CLIPS build command.

        """
        if lib.EnvBuild(self._env, construct.encode()) != 1:
            raise CLIPSError(self._env)

    def eval(self, construct):
        """Evaluate an expression returning its value.

        The Python equivalent of the CLIPS eval command.

        """
        data = clips.data.DataObject(self._env)

        if lib.EnvEval(self._env, construct.encode(), data.byref) != 1:
            raise CLIPSError(self._env)

        return data.value

    def reset(self):
        """Reset the CLIPS environment.

        The Python equivalent of the CLIPS reset command.

        """
        lib.EnvReset(self._env)

    def clear(self):
        """Clear the CLIPS environment.

        The Python equivalent of the CLIPS clear command.

        """
        lib.EnvClear(self._env)

    def define_function(self, function):
        """Define the Python function within the CLIPS environment.

        Functions defined in this way can be called within CLIPS
        via the 'python-function' symbol.

        (python-function function_name arg1 arg2)

        """
        ENVIRONMENT_DATA[self._env].user_functions[function.__name__] = function


@ffi.def_extern()
def python_function(env, data_object):
    arguments = []
    temp = clips.data.DataObject(env)
    data = clips.data.DataObject(env, data=data_object)
    argnum = lib.EnvRtnArgCount(env)

    if lib.EnvArgTypeCheck(
            env, b'python-function', 1, CLIPSType.SYMBOL, temp.byref) != 1:
        raise RuntimeError()

    funcname = temp.value

    for index in range(2, argnum + 1):
        lib.EnvRtnUnknown(env, index, temp.byref)
        arguments.append(temp.value)

    try:
        ret = ENVIRONMENT_DATA[env].user_functions[funcname](*arguments)
    except Exception as error:
        ret = str("%s: %s" % (error.__class__.__name__, error))

    data.value = ret if ret is not None else clips.common.Symbol('nil')
