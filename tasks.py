from invoke import task


@task
def isort(c):  # type: ignore
    c.run("isort -rc .")


@task
def black(c):  # type: ignore
    c.run("black .")


@task
def mypy(c):  # type: ignore
    c.run("mypy . --ignore-missing-imports")


@task
def lint(c):  # type: ignore
    isort(c)
    black(c)
    mypy(c)