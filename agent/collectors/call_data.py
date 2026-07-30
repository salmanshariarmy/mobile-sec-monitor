import subprocess


def get_calls():

    calls = []

    try:

        output = subprocess.check_output(
            [
                "content",
                "query",
                "--uri",
                "content://call_log/calls",
                "--projection",
                "number:date:duration:type"
            ],
            text=True
        )


        for line in output.splitlines():

            if line.startswith("Row"):

                calls.append(line)


    except Exception as e:

        calls.append(
            str(e)
        )


    return calls
