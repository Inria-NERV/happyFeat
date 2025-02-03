# Documentation

You can build the documentation locally. 

For that, you will need **mkdocs** and **mkdocs-material**, which you can install using **pip**, **conda** or **brew**.

Clone HappyFeat's repository:

- SSH: `git clone git@github.com:Inria-NERV/happyFeat.git`

- HTTPS: `git clone https://github.com/Inria-NERV/happyFeat` 

Then, go to the clones repository, make sure you are on the branch of your choice (e.g. `main` or `develop`), and type:

```shell
mkdocs build
```

The documentation will be built in the folder `site`.