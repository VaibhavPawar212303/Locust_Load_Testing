from locust import task, run_single_user
from locust import FastHttpUser


class har_file(FastHttpUser):
    host = "http://testphp.vulnweb.com"
    default_headers = {
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    }

    @task
    def t(self):
        with self.client.request(
            "GET",
            "/login.php",
            headers={"Referer": "http://testphp.vulnweb.com/"},
            catch_response=True,
        ) as resp:
            pass
        with self.client.request("GET", "/", catch_response=True) as resp:
            pass
        with self.client.request(
            "GET",
            "/login.php",
            headers={"Referer": "http://testphp.vulnweb.com/"},
            catch_response=True,
        ) as resp:
            pass
        with self.client.request(
            "POST",
            "/userinfo.php",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "http://testphp.vulnweb.com",
                "Referer": "http://testphp.vulnweb.com/login.php",
            },
            data="uname=test&pass=test",
            catch_response=True,
        ) as resp:
            pass
        with self.client.request(
            "POST",
            "/userinfo.php",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "http://testphp.vulnweb.com",
                "Referer": "http://testphp.vulnweb.com/userinfo.php",
            },
            data="urname=Pedro+Miguel&ucc=5555555555554444&uemail=fgh&uphone=1234&uaddress=HtTpS%3A%2F%2F8643483865116723546.whatdoesascannersee.com&update=update",
            catch_response=True,
        ) as resp:
            pass
        with self.client.request(
            "GET",
            "/categories.php",
            headers={"Referer": "http://testphp.vulnweb.com/userinfo.php"},
            catch_response=True,
        ) as resp:
            pass
        with self.client.request(
            "GET",
            "/index.php",
            headers={"Referer": "http://testphp.vulnweb.com/categories.php"},
            catch_response=True,
        ) as resp:
            pass
        with self.client.request(
            "GET",
            "/artists.php",
            headers={"Referer": "http://testphp.vulnweb.com/index.php"},
            catch_response=True,
        ) as resp:
            pass
        with self.client.request(
            "GET",
            "/cart.php",
            headers={"Referer": "http://testphp.vulnweb.com/artists.php"},
            catch_response=True,
        ) as resp:
            pass
        with self.client.request(
            "GET",
            "/userinfo.php",
            headers={"Referer": "http://testphp.vulnweb.com/cart.php"},
            catch_response=True,
        ) as resp:
            pass
        with self.client.request(
            "GET",
            "/AJAX/index.php",
            headers={"Referer": "http://testphp.vulnweb.com/userinfo.php"},
            catch_response=True,
        ) as resp:
            pass
        with self.client.request(
            "GET",
            "/userinfo.php",
            headers={"Referer": "http://testphp.vulnweb.com/cart.php"},
            catch_response=True,
        ) as resp:
            pass
        with self.client.request(
            "GET",
            "/logout.php",
            headers={"Referer": "http://testphp.vulnweb.com/userinfo.php"},
            catch_response=True,
        ) as resp:
            pass


if __name__ == "__main__":
    run_single_user(har_file)
