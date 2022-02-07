#!/usr/bin/python3

import os
import inspect
import ast
import logging
log = logging.getLogger(__name__)

import typer

##########################################################################
# The menu support routines
##########################################################################

class Menu(object):
    def __init__(self, options=None, title=None, message=None, prompt=">>>",
                 refresh=lambda: None, auto_clear=True):
        if options is None:
            options = []
        self.options = None
        self.title = None
        self.is_title_enabled = None
        self.message = None
        self.is_message_enabled = None
        self.refresh = None
        self.prompt = None
        self.is_open = None
        self.auto_clear = auto_clear
        
        self.set_options(options)
        self.set_title(title)
        self.set_title_enabled(title is not None)
        self.set_message(message)
        self.set_message_enabled(message is not None)
        self.set_prompt(prompt)
        self.set_refresh(refresh)

    def set_options(self, options):
        original = self.options
        self.options = []
        try:
            for option in options:
                if not isinstance(option, tuple):
                    raise TypeError(option, "option is not a tuple")
                if len(option) < 2:
                    raise ValueError(option, "option is missing a handler")
                kwargs = option[2] if len(option) == 3 else {}
                self.add_option(option[0], option[1], kwargs)
        except (TypeError, ValueError) as e:
            self.options = original
            raise e

    def set_title(self, title):
        self.title = title

    def set_title_enabled(self, is_enabled):
        self.is_title_enabled = is_enabled

    def set_message(self, message):
        self.message = message

    def set_message_enabled(self, is_enabled):
        self.is_message_enabled = is_enabled

    def set_prompt(self, prompt):
        self.prompt = prompt

    def set_refresh(self, refresh):
        if not callable(refresh):
            raise TypeError(refresh, "refresh is not callable")
        self.refresh = refresh

    def add_option(self, name, handler, kwargs):
        if not callable(handler):
            raise TypeError(handler, "handler is not callable")
        self.options += [(name, handler, kwargs)]

    # open the menu
    def open(self):
        self.is_open = True
        while self.is_open:
            self.refresh()
            func = self.input()
            if func == Menu.CLOSE:
                func = self.close
            print()
            func()

    def close(self):
        self.is_open = False

    # clear the screen
    # show the options
    def show(self):
        if self.auto_clear:
            os.system('cls' if os.name == 'nt' else 'clear')
        if self.is_title_enabled:
#            print(self.title)
            typer.secho(self.title, fg=typer.colors.BRIGHT_BLUE)
            print()
        if self.is_message_enabled:
            typer.echo(self.message)
            print()
        for (index, option) in enumerate(self.options):
            num = typer.style(str(index + 1), fg=typer.colors.GREEN, bold=True)
            typer.echo("   " + num + ". " + option[0])
#            print(str(index + 1) + ". " + option[0])
        print()
#        print("ENTER to exit")
        typer.secho("ENTER to exit", fg=typer.colors.GREEN)
        print()

    # show the menu
    # get the option index from the input
    # return the corresponding option handler
    def input(self):
        if len(self.options) == 0:
            return Menu.CLOSE
        try:
            self.show()
            inp = input(self.prompt + " ")
            if inp == "":
                return Menu.CLOSE
            index = int(inp) - 1
            option = self.options[index]
            handler = option[1]
            if handler == Menu.CLOSE:
                return Menu.CLOSE
            kwargs = option[2]
            return lambda: handler(**kwargs)
        except (ValueError, IndexError):
            return self.input()

    def CLOSE(self):
        pass


def get_arguments(argument_definitions):

    arguments = []
    for arg in argument_definitions:

        name = arg["name"]
        prompt = arg["prompt"]
        # Get the argument type, with default str if the key does not exist
        arg_type = arg.get("type", "str")

        if arg_type == "bool":
            if arg["default"] == True:
                prompt = prompt + " [Y/n]"
            else:
                prompt = prompt + " [N/y]"

        if arg_type == "str":
            prompt = prompt + " [" + arg.get("default", "") + "]"

        prompt = prompt + ": "
        
        s = input(prompt)

        if s == "":
            s = arg["default"]

        if arg_type == "bool":
            true_values = (True, "Y", "y")
            if s in true_values:
                s = True
            else:
                s = False

        arguments.append(s)
    
    return arguments

def invoke(operation):
    # Check if the operation is a function
    if not (inspect.isfunction(operation) or inspect.ismethod(operation)) :
        log.error(f"{operation} is not a function or method")
        input("Press a key")
        return

    # Get the docstring and split in lines
    doc = inspect.getdoc(operation)

    # Signal error if the function does not have a docstring
    if doc is None or len(doc) == 0:
        doc_lines = []
    else:
        doc_lines = doc.splitlines()

    # The docstring should be formatted in a specific way.
    # The first lines are the "normal" function documentation
    # Then a separator, exactly as: "--- Definitions ---"
    # Finally, one line per argument, formatted as a dict:
    # {"name": "compile", "type": "bool", "prompt": "Compile contracts?", "default": True}
    # If the separator line does not exist or no definitions, assume the function has zero arguments

    docs = []
    argument_definitions = []
    separator_found = False
    for l in doc_lines:
        if l == "--- Definitions ---":
            separator_found = True
            continue
        if separator_found:
            p = ast.literal_eval(l)
            argument_definitions.append(p)
        else:
            docs.append(l)
    
    # Print the comment of the function
    for l in docs:
        print(l)

    args = get_arguments(argument_definitions)
    operation(*args)

    input("\nPress enter to continue")

