import subprocess


def get_sms():

    sms = []

    try:

        output = subprocess.check_output(
            [
                "content",
                "query",
                "--uri",
                "content://sms",
                "--projection",
                "address:body:date"
            ],
            text=True
        )


        for line in output.splitlines():

            if line.startswith("Row"):

                sms.append(line)


    except Exception as e:

        sms.append(
            str(e)
        )


    return sms
