import setuptools

setuptools.setup(
    name='lobster_simulator',
    version='0.0.1',
    description='Simulator for the Lobster uuv',
    url='https://github.com/LOBSTER-Robotics/LobsterSimulator',
    author='Joris Quist',
    author_email='Jorisquist@gmail.com',
    license='',
    packages= setuptools.find_packages(),
    install_requires=['pybullet',
                      'numpy'
                      ],

    classifiers=[],
)
