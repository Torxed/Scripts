import logging
import os
import sys
from pathlib import Path
from typing import Dict, Union, List, Any, Callable, Optional

from dataclasses import asdict, is_dataclass

log_adapter = None

class Journald:
	@staticmethod
	def log(message :str, level :int = logging.DEBUG) -> None:
		try:
			import systemd.journal  # type: ignore
		except ModuleNotFoundError:
			return None

		global log_adapter
		if log_adapter is None:
			log_adapter = logging.getLogger('spfcheck')

			log_fmt = logging.Formatter('{"level": "%(levelname)s", "message": "%(message)s"}')
			log_ch = systemd.journal.JournalHandler()
			log_ch.setFormatter(log_fmt)
			log_adapter.addHandler(log_ch)
			log_adapter.setLevel(logging.DEBUG)

		# Convert to JSON for easier post-processing
		log_adapter.log(level, message.replace('"', '\\"'))

# Found first reference here: https://stackoverflow.com/questions/7445658/how-to-detect-if-the-console-does-support-ansi-escape-codes-in-python
# And re-used this: https://github.com/django/django/blob/master/django/core/management/color.py#L12
def supports_color() -> bool:
	"""
	Return True if the running system's terminal supports color,
	and False otherwise.
	"""
	supported_platform = sys.platform != 'win32' or 'ANSICON' in os.environ

	# isatty is not always implemented, #6223.
	is_a_tty = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
	return supported_platform and is_a_tty


# Heavily influenced by: https://github.com/django/django/blob/ae8338daf34fd746771e0678081999b656177bae/django/utils/termcolors.py#L13
# Color options here: https://askubuntu.com/questions/528928/how-to-do-underline-bold-italic-strikethrough-color-background-and-size-i
def stylize_output(text: str, *opts :str, **kwargs) -> str:
	"""
	Adds styling to a text given a set of color arguments.
	"""
	opt_dict = {'bold': '1', 'italic': '3', 'underscore': '4', 'blink': '5', 'reverse': '7', 'conceal': '8'}
	colors = {
		'black' : '0',
		'red' : '1',
		'green' : '2',
		'yellow' : '3',
		'blue' : '4',
		'magenta' : '5',
		'cyan' : '6',
		'white' : '7',
		'teal' : '8;5;109',      # Extended 256-bit colors (not always supported)
		'orange' : '8;5;208',    # https://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html#256-colors
		'darkorange' : '8;5;202',
		'gray' : '8;5;246',
		'grey' : '8;5;246',
		'darkgray' : '8;5;240',
		'lightgray' : '8;5;256'
	}
	foreground = {key: f'3{colors[key]}' for key in colors}
	background = {key: f'4{colors[key]}' for key in colors}
	reset = '0'

	code_list = []
	if text == '' and len(opts) == 1 and opts[0] == 'reset':
		return '\x1b[%sm' % reset

	for k, v in kwargs.items():
		if k == 'fg':
			code_list.append(foreground[str(v)])
		elif k == 'bg':
			code_list.append(background[str(v)])

	for o in opts:
		if o in opt_dict:
			code_list.append(opt_dict[o])

	if 'noreset' not in opts:
		text = '%s\x1b[%sm' % (text or '', reset)

	return '%s%s' % (('\x1b[%sm' % ';'.join(code_list)), text or '')


def log(*args :str, **kwargs :Union[str, int, Dict[str, Union[str, int]]]) -> None:
	string = orig_string = ' '.join([str(x) for x in args])

	if kwargs.get('level') == logging.DEBUG and kwargs.get('fg') is None:
		kwargs['fg'] = 'gray'
	elif kwargs.get('level') == logging.ERROR and kwargs.get('fg') is None:
		kwargs['fg'] = 'red'
	elif kwargs.get('level') == logging.WARNING and kwargs.get('fg') is None:
		kwargs['fg'] = 'yellow'

	# Attempt to colorize the output if supported
	# Insert default colors and override with **kwargs
	if supports_color():
		kwargs = {'fg': 'white', **kwargs}
		string = stylize_output(string, **kwargs)

	Journald.log(string, level=int(str(kwargs.get('level', logging.INFO))))

	sys.stdout.write(f"{string}\n")
	sys.stdout.flush()
