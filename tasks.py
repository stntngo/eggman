from invoke import task


@task
def isort(c):  # type: ignore
    c.run("isort -rc .")


@task
def black(c):  # type: ignore
    c.run("black .")


@task
def lint(c):  # type: ignore
    isort(c)
    black(c)
