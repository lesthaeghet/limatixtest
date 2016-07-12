import shutil
import os.path
from setuptools import setup
from setuptools.command.install_lib import install_lib
from setuptools.command.install import install
import setuptools.command.bdist_egg
import sys
import glob

exclude_directories = lambda files: [ file for file in files if not os.path.isdir(file) ]

share_checklist_files=glob.glob("checklists/*")
pt_steps_files=glob.glob("pt_steps/*")
conf_files=glob.glob("conf/*")
doc_files=exclude_directories(glob.glob("doc/*"))
doc_pte_files=exclude_directories(glob.glob("doc/processtrak_example/*"))
doc_pte_creston_files=exclude_directories(glob.glob("doc/processtrak_example/creston_jan2016/*"))
xslt_files=glob.glob("xslt/*")
root_files=["README.txt","INSTALL.txt"]
#limatix_widgets_glade_catalogs_package_files=["*.xml"]
limatix_widgets_package_files=["*.glade","glade_catalogs/*"]
limatix_checklist_steps_package_files=["*.glade"]
limatix_package_files=["*.glade"]

console_scripts=["datacollect2",
                 "dc_checklist",
                 "pt_checkprovenance",
                 "dc_chx2chf",
                 "dc_glade",
                 "dc_gui",
                 "dc_paramdb2",
                 "thermal2limatix",
                 "processtrak",
                 "dc_ricohphoto",
                 "dc_xlg2dpd",
                 "pt_cleanup"]
gui_scripts = []  # Could move graphical scrips into here to eliminate stdio window on Windows (where would error messages go?)

console_scripts_entrypoints = [ "%s = limatix.bin.%s:main" % (script,script) for script in console_scripts ]
gui_scripts_entrypoints = [ "%s = limatix.bin.%s:main" % (script,script) for script in gui_scripts ]

canonicalize_path_config_files=["limatix/canonicalize_path/canonical_paths.conf.example","limatix/canonicalize_path/tag_index_paths.conf.example"]
canonicalize_path_package_files=["canonical_paths.conf","tag_index_paths.conf"]

limatix_checklist_step_paths=glob.glob("limatix/steps/*.py")
limatix_checklist_step_names=[ os.path.splitext(os.path.split(path)[1])[0] for path in limatix_checklist_step_paths if not path.endswith("__init__.py")]
limatix_checklist_step_entrypoints = [ '%s = limatix.steps.%s' % (stepname,stepname) for stepname in limatix_checklist_step_names]

limatix_widget_paths=glob.glob("limatix/widgets/*.py")
limatix_widget_names=[ os.path.splitext(os.path.split(path)[1])[0] for path in limatix_widget_paths if not path.endswith("__init__.py")]
limatix_widget_entrypoints = [ '%s = limatix.widgets.%s' % (widgetname,widgetname) for widgetname in limatix_widget_names]

#package_files=["canonical_paths.conf","tag_index_paths.conf"]

# NOTE ***: share files will be installed to prefix/share/limatix
# By default, prefix is /usr so share_files to be found in
# /usr/share/limatix

# Apply hotfix to setuptools issue #130, from 
# https://bitbucket.org/pypa/setuptools/issues/130/install_data-doesnt-respect-prefix
# hotfix applies at least to all setuptools versions prior to 20.2

def setuptools_command_bdist_egg_call_command_hotfix(self, cmdname, **kw):
    """Invoke reinitialized command `cmdname` with keyword args"""
    if cmdname != 'install_data':
        for dirname in INSTALL_DIRECTORY_ATTRS:
            kw.setdefault(dirname, self.bdist_dir)
    kw.setdefault('skip_build', self.skip_build)
    kw.setdefault('dry_run', self.dry_run)
    cmd = self.reinitialize_command(cmdname, **kw)
    self.run_command(cmdname)
    return cmd

setuptools_version=tuple([int(versionpart) for versionpart in setuptools.__version__.split(".")])

# Apply hotfix to all versions prior to 20.2
if setuptools_version < (20,2):
    setuptools.command.bdist_egg.call_command=setuptools_command_bdist_egg_call_command_hotfix
    pass




class install_lib_save_prefix(install_lib):
    """Save a file install_prefix.txt with the install prefix"""
    def run(self):
        install_lib.run(self)
        
        #sys.stderr.write("\nprefix:" + str((self.distribution.command_obj["install"].prefix))+"\n\n\n")
        
        #sys.stderr.write("\ninstall_dir:" + self.install_dir+"\n\n\n")
        #sys.stderr.write("\npackages:" + str(self.distribution.command_obj["build_py"].packages)+"\n\n\n")

        for package in self.distribution.command_obj["build_py"].packages:
            install_dir=os.path.join(*([self.install_dir] + package.split('.')))
            fh=open(os.path.join(install_dir,"install_prefix.txt"),"w")
            fh.write(self.distribution.command_obj["install"].prefix)
            fh.close()
            pass
        pass
    pass


setup(name="limatix",
      description="Automated data collection",
      author="Stephen D. Holland",
      # url="http://limatix.org/dataguzzler",
      zip_safe=False,
      packages=["limatix",
                "limatix.steps",
                "limatix.bin",
                "limatix.widgets", 
                "limatix.canonicalize_path", 
                "limatix.dc_lxml_treesync"],
      package_dir={"limatix.canonicalize_path": "limatix/canonicalize_path/canonicalize_path"},
      cmdclass={"install_lib": install_lib_save_prefix},
      data_files=[ ("share/limatix/checklists",share_checklist_files),
                   ("share/limatix/pt_steps",pt_steps_files),
                   ("share/limatix/conf",conf_files),
                   ("share/limatix/doc",doc_files),
                   ("share/limatix/doc/processtrak_example",doc_pte_files),
                   ("share/limatix/doc/processtrak_example/creston_jan2016",doc_pte_creston_files),
                   ("share/limatix/xslt",xslt_files),
                   ("share/limatix",root_files),
                   ("etc/canonicalize_path",canonicalize_path_config_files)],
      package_data={"limatix.canonicalize_path": canonicalize_path_package_files, 
                    "limatix.widgets": limatix_widgets_package_files,
                    "limatix.steps": limatix_checklist_steps_package_files,
                    "limatix": limatix_package_files},
      entry_points={"limatix.checklist.step": limatix_checklist_step_entrypoints,
                    "limatix.widget": limatix_widget_entrypoints,
                    "console_scripts": console_scripts_entrypoints,
                    "gui_scripts": gui_scripts_entrypoints })




#      scripts=["bin/datacollect2",
#               "bin/dc_checklist",
#               "bin/pt_checkprovenance",
#               "bin/dc_chx2chf",
#               "bin/dc_glade",
#               "bin/dc_gui",
#               "bin/dc_paramdb2",
#               "bin/thermal2limatix",
#               "bin/processtrak",
#               "bin/dc_ricohphoto",
#               "bin/dc_xlg2dpd",
#               "bin/pt_cleanup"],




