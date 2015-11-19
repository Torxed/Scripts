import glob
from os import walk, chdir, remove, makedirs
from shutil import rmtree, move
from os.path import abspath
from subprocess import Popen, PIPE
from time import strftime

project_name = None # Will be fetched from each .i file
setup_template = None # Will be populated in the first cleanup() call
mute_output = True

def isfile(path):
	return glob.glob(path)

def run(cmd):
	handle = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
	output, errors = b'', b''
	while handle.poll() is None:
		output += handle.stdout.readline()
		errors += handle.stderr.readline()
	handle.stdout.close()
	handle.stderr.close()

	if (not mute_output and len(output)) or len(errors):
		print('Output:',output)
		print('Errors:',errors)

def package():
	dst = abspath('./'+project_name)
	if isfile(dst):
		backup_dst = abspath('./'+project_name+'_'+strftime('%Y_%m_%d_%H-%M-%S/'))
		makedirs(backup_dst)
		move(dst, abspath(backup_dst))
		
	makedirs(dst)
	move(abspath('./'+project_name+'.py'), dst)
	move(glob.glob(abspath('./_'+project_name+'*.so'))[0], dst)

	functions = []
	with open(abspath('./'+project_name+'.h'), 'r') as fh:
		for line in fh:
			_type_, name = line.split(' ',1)
			name, params = name.split('(',1)
			functions.append(name)

	if len(functions):
		with open(abspath(dst+'/__init__.py'), 'w') as fh:
			fh.write('from ' + project_name+'.'+project_name + ' import ' + ', '.join(functions) + '\n')
			fh.write('__all__ = [\'' + ', \''.join(functions) + '\']\n')

def cleanup(save_setups=True):
	global project_name
	global setup_template

	if isfile(abspath('./build')):
		rmtree(abspath('./build'))
	if project_name and isfile(abspath('./'+project_name+'_wrap.c')):
		remove(abspath('./'+project_name+'_wrap.c'))
	if project_name and isfile(abspath('./'+project_name+'_wrap.cxx')):
		remove(abspath('./'+project_name+'_wrap.cxx'))

	if not save_setups:
		if isfile(abspath('./setup.py')):
			remove(abspath('./setup.py'))

	project_name = None
	setup_template = """#!/usr/bin/env python

# -- setup.py file for SWIG

from distutils.core import setup, Extension


module_data = Extension('_%%moduleName%%',
                           sources=['%%moduleName%%_wrap.c', '%%moduleName%%.c'],
                           )

setup (name = '%%moduleName%%',
       version = '0.1',
       author      = "SWIG Docs",
       description = "Simple swig example from docs",
       ext_modules = [module_data],
       py_modules = ["%%moduleName%%"]
       )

	"""

for root, dirs, files in walk(abspath('./')):

	for fileName in files:
		path = abspath(root +'/'+ fileName)
		fileName_noext, ext = path.rsplit('.', 1)

		if ext == 'i':
			cleanup(save_setups=True) #!Important
			chdir(root)

			with open(path, 'r') as fh:
				for line in fh:
					if line[:7] == r'%module':
						project_name = line[8:].strip()
			if project_name is None:
				raise KeyError(r'Module name is required in the *.i file, add a line "%module <module name>" somewhere.')

			run('swig -python ' + fileName)
			found_save = False

			if isfile(fileName_noext + '_wrap.c') or isfile(fileName_noext + '_wrap.cxx'):
				print('* Successfully created a swig wrapper script')

				if isfile('setup.py'):
					found_save = True
					print(' - A "setup.py" already excists in "' + root + '", will try to use it.')
				else:
					with open('setup.py', 'w') as fh:
						setup_template = setup_template.replace('%%moduleName%%', project_name)
						fh.write(setup_template)

				run('python setup.py build_ext --inplace')
				if isfile('_'+project_name+'*.so'):
					print('Successfully packaged "' + project_name + '"')

					package()
					cleanup(save_setups=found_save)
			else:
				raise KeyError('No *_wrap.c/cxx file was created. Aborting.')