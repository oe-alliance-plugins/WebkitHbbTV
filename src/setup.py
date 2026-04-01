from setuptools import setup
import setup_translate

pkg = 'Extensions.WebkitHbbTV'
setup(name='enigma2-plugin-extensions-webkithbbtv',
       version='3.0',
       description='E2 HbbTV Plugin',
       package_dir={pkg: 'WebkitHbbTV'},
       packages=[pkg],
       package_data={pkg: ['images/*.png', '*.png', '*.xml', 'locale/*/LC_MESSAGES/*.mo']},
       cmdclass=setup_translate.cmdclass,  # for translation
      )
