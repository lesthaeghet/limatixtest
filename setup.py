import shutil
import os.path
from setuptools import setup
from setuptools.command.install_lib import install_lib
from setuptools.command.install import install
import setuptools.command.bdist_egg
import sys
import glob

share_checklist_files=glob.glob("checklists/*")
dcp_steps_files=glob.glob("dcp_steps/*")
conf_files=glob.glob("conf/*")
doc_files=glob.glob("doc/*")
root_files=["README.txt","INSTALL.txt"]
datacollect2_widgets_package_files=["glade-3/glade_catalogs/*"]
datacollect2_widgets_package_files=["*.glade"]
datacollect2_steps_package_files=["*.glade"]
datacollect2_package_files=["*.glade"]

canonicalize_path_config_files=["datacollect2/canonicalize_path/canonical_paths.conf.example","datacollect2/canonicalize_path/tag_index_paths.conf.example"]
canonicalize_path_package_files=["canonical_paths.conf","tag_index_paths.conf"]


#package_files=["canonical_paths.conf","tag_index_paths.conf"]

# NOTE ***: share files will be installed to prefix/share/datacollect2
# By default, prefix is /usr so share_files to be found in
# /usr/share/datacollect2

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


setup(name="datacollect2",
      description="Automated data collection",
      author="Stephen D. Holland",
      # url="http://thermal.cnde.iastate.edu/dataguzzler",
      zip_safe=False,
      packages=["datacollect2",
                "datacollect2.steps",
                "datacollect2.widgets", 
                "datacollect2.canonicalize_path", 
                "datacollect2.dc_lxml_treesync"],
      package_dir={"datacollect2.canonicalize_path": "datacollect2/canonicalize_path/canonicalize_path"},
      cmdclass={"install_lib": install_lib_save_prefix},
      data_files=[ ("share/datacollect2/checklists",share_checklist_files),
                   ("share/datacollect2/dcp_steps",dcp_steps_files),
                   ("share/datacollect2/conf",conf_files),
                   ("share/datacollect2/doc",doc_files),
                   ("share/datacollect2",root_files),
                   ("etc/canonicalize_path",canonicalize_path_config_files)],
      package_data={"datacollect2.canonicalize_path": canonicalize_path_package_files, 
                    "datacollect2.widgets": datacollect2_widgets_package_files,
                    "datacollect2.steps": datacollect2_steps_package_files,
                    "datacollect2": datacollect2_package_files},
      scripts=["bin/datacollect2",
               "bin/dc_checklist",
               "bin/dc_checkprovenance",
               "bin/dc_chx2chf",
               "bin/dc_glade",
               "bin/dc_gui",
               "bin/dc_paramdb2",
               "bin/dc_process",
               "bin/dc_ricohphoto",
               "bin/dc_xlg2dpd"])





