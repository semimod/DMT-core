FROM registry.gitlab.com/dmt-development/dmt-core:base 

# runtime version of Hdev
RUN git clone https://gitlab.com/metroid120/hdev_simulator.git && cd hdev_simulator/HdevPy && pip install -e .

RUN cd /home/local/bin && wget "https://gitlab.com/metroid120/hdev_simulator/-/jobs/artifacts/master/raw/builddir_docker/hdev?job=build:linux" -O hdev && chmod +x hdev
# installed version of pip
COPY . /dmt/
RUN cd /dmt && mkdir logs && pip install  --upgrade --upgrade-strategy eager -e .[full]

# make a short test to ensure that the container is good...
RUN cd /dmt && pytest --cov=DMT/ test/test_core_no_interfaces/

# apply read-write rights to some files inside the container for everyone 
RUN chmod --recursive a+rw /dmt && chmod --recursive a+rw /home/local/bin 
