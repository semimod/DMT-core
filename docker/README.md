# DMT docker container

This is quite straight forward:

```bash
    docker login registry.gitlab.com
```

Then the example bash script in `dmt` can be used to execute Python scripts which call DMT. 

```bash
    dmt dmt_script.py
```

## Installing container dependencies

If you want to install more programs or Python packages into this container, we recommend creating your own container. The Dockerfile would start like this:

```Dockerfile
    FROM registry.gitlab.com/dmt-development/dmt-core:full
```

Build and tag this file with your own name. Then change the `dmt` bash script to use the new container accordingly.

## Exchange data

Per default, the bash script mounts the local folder into the container under `/pwd` and hence all data inside the current working path is available there. If you only use local paths (also for the simulation data and reports), the borders between host and guest are transparent. Be aware, that inside the container the user `dmt_user` (id: 1000, group: 1000) is used. So if you have a different id, change the script accordingly. It may look like this (untested):

```bash
    chmod a+rw -r . # here to allow the files inside the current working directory to be read and rewritten in the container
    docker run --rm -ti \
        --env="DISPLAY" \
        --user 1000:1000 \
        --volume="/tmp/.X11-unix:/tmp/.X11-unix:rw" \
        --volume "${PWD}":/pwd \
        --workdir=/pwd \
        registry.gitlab.com/dmt-development/dmt-core:full \
        "python3 $@; chmod a+rw -r ." # here to allow the files created in the container to be used in the host system
```

Depending on your use case, you may restrict the exchange to one direction or special folders, this would decrease runtime. 

## Configuration

In this folder also an example configuration is given. The idea is to have all created files, i.e. from simulators or saved measurements, inside the current working directory. If you generate reports or plots using `dmt` make sure, that the same principle is applied there.


## Issues, verification and Windows batch file

If you tested and verified/improved the script, please report this to us!
