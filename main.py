from fastapi import APIRouter, FastAPI, Response
import subprocess
import time
import os
import csv
import json
from typing import Optional
import json
from fastapi import FastAPI, APIRouter, File, Response, UploadFile, HTTPException
import csv
import subprocess
import time
import os
from typing import Optional, List

app = FastAPI()
router = APIRouter()

@router.post("/distributedLoadTest/")
def distributed_load_test(
    url: str, 
    durationInSec: str, 
    concurrentUser: str, 
    rampusers: str,
    endpoint: str, 
    method: str = "GET", 
    payload: Optional[str] = None,
    workers: int = 1
):
    # Function to generate the Locustfile
    def generate_locustfile(url: str, endpoint: str, method: str, payload: Optional[str] = None):
        payload_str = payload if payload is not None else '{}'
        locustfile_content = f"""
from locust import HttpUser, task, between

class MyUser(HttpUser):
    host = "{url}"
    wait_time = between(1, 3)

    @task
    def my_task(self):
        with self.client.request("{method}", "{url}{endpoint}", json={payload_str}) as response:
            if response.status_code != 200:
                print(f"Error: Request failed with status code {{response.status_code}}")
"""
        locustfile_path = "locustfile.py"
        with open(locustfile_path, "w") as f:
            f.write(locustfile_content)
        return locustfile_path

    # Generate Locustfile
    locustfile_path = generate_locustfile(url, endpoint, method, payload)

    # Ensure Docker Compose setup and run Locust
    current_dir = os.getcwd().replace("\\", "/")
    
    try:
        subprocess.run(f"docker-compose up -d --scale locust_worker={workers}", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"Failed to start Docker services: {str(e)}"}

    time.sleep(5)  # Ensure containers are fully up and running

    locust_command = (
        f"docker exec locust_master locust -f /mnt/locust/locustfile.py --headless "
        f"-H {url} -r {rampusers} -t {durationInSec}s -u {concurrentUser} "
        f"--csv=/mnt/locust/locust_report --html=/mnt/locust/report.html"
    )
    try:
        subprocess.run(locust_command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"An error occurred during the load test: {str(e)}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

    # Additional delay to ensure reports are written
    time.sleep(30)

    summary_stats = {"stats": [], "failures": []}

    try:
        with open("locust_report_stats.csv", "r") as stats_file:
            reader = csv.DictReader(stats_file)
            for row in reader:
                summary_stats["stats"].append(row)
    except FileNotFoundError as e:
        return {"error": "Failed to read Locust stats CSV report", "details": str(e)}

    try:
        with open("locust_report_failures.csv", "r") as failures_file:
            reader = csv.DictReader(failures_file)
            for row in reader:
                summary_stats["failures"].append(row)
    except FileNotFoundError as e:
        return {"error": "Failed to read Locust failures CSV report", "details": str(e)}

    json_object = json.dumps(summary_stats, indent=4)

    with open("report.json", "w") as outfile:
        outfile.write(json_object)
    
    # Clean up Docker services
    subprocess.run("docker-compose down", shell=True, check=True)

    return {
        "Url": url,
        "DurationInSec": durationInSec,
        "ConcurrentUser": concurrentUser,
        "Endpoint": endpoint,
        "Method": method,
        "Payload": payload,
        "message": "Load test completed successfully, reports generated.",
        "json_report": summary_stats,
        "html_report_path": os.path.join(current_dir, "report.html")
    }

@router.post("/distributedLoadTestWithCSV/")
async def distributed_load_test_with_csv(
    url: str, 
    durationInSec: str, 
    concurrentUser: str, 
    rampusers: str,
    file: Optional[UploadFile] = File(None),
    workers: int = 1
):
    def generate_locustfile(scenarios: List[dict]):
        locustfile_content = """
from locust import HttpUser, task, between

class MyUser(HttpUser):
    wait_time = between(1, 3)
        """
        for idx, scenario in enumerate(scenarios):
            task_name = f"task_{idx+1}"
            method = scenario.get("method", "GET")
            endpoint = scenario["endpoint"]
            payload = scenario.get("payload", {})
            locustfile_content += f"""
    @task
    def {task_name}(self):
        with self.client.request("{method}", "{scenario['url']}{endpoint}", json={json.dumps(payload)}) as response:
            if response.status_code != 200:
                print(f"Error: Request to {endpoint} failed with status code {{response.status_code}}")
            """
        locustfile_path = "locustfile.py"
        with open(locustfile_path, "w") as f:
            f.write(locustfile_content)
        return locustfile_path

    scenarios = []
    if file:
        try:
            contents = await file.read()
            decoded_content = contents.decode("utf-8").splitlines()
            reader = csv.DictReader(decoded_content, delimiter=',')
            for row in reader:
                try:
                    payload_str = row.get("payload", "{}")
                    payload_str = payload_str.replace('""', '"')
                    payload_json = json.loads(payload_str) if payload_str else {}
                    scenarios.append({
                        "url": row.get("url", url),
                        "endpoint": row.get("endpoint", ""),
                        "method": row.get("method", "GET"),
                        "payload": payload_json
                    })
                except json.JSONDecodeError as e:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON in payload: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV file: {str(e)}")
    else:
        return {"error": "CSV file is required for this operation."}

    locustfile_path = generate_locustfile(scenarios)
    time.sleep(10)  # Ensure locustfile is written

    current_dir = os.getcwd().replace("\\", "/")

    try:
        subprocess.run(f"docker-compose up -d --scale locust_worker={workers}", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"Failed to start Docker services: {str(e)}"}

    time.sleep(5)  # Ensure containers are fully up and running

    try:
        locust_command = (
            f"docker exec locust_master locust -f /mnt/locust/locustfile.py --headless "
            f"--host {url} -r {rampusers} -t {durationInSec}s -u {concurrentUser} "
            f"--csv=/mnt/locust/locust_report --html=/mnt/locust/report.html"
        )
        subprocess.run(locust_command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"An error occurred during the load test: {str(e)}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

    time.sleep(30)  # Additional delay to ensure reports are written

    summary_stats = {"stats": [], "failures": []}

    try:
        with open("locust_report_stats.csv", "r") as stats_file:
            reader = csv.DictReader(stats_file)
            for row in reader:
                summary_stats["stats"].append(row)
    except FileNotFoundError as e:
        return {"error": "Failed to read Locust stats CSV report", "details": str(e)}

    try:
        with open("locust_report_failures.csv", "r") as failures_file:
            reader = csv.DictReader(failures_file)
            for row in reader:
                summary_stats["failures"].append(row)
    except FileNotFoundError as e:
        return {"error": "Failed to read Locust failures CSV report", "details": str(e)}

    json_object = json.dumps(summary_stats, indent=4)

    with open("report.json", "w") as outfile:
        outfile.write(json_object)

    subprocess.run(f"docker-compose down", shell=True, check=True)

    return {
        "Url": url,
        "DurationInSec": durationInSec,
        "ConcurrentUser": concurrentUser,
        "message": "Load test completed successfully, reports generated.",
        "json_report": summary_stats,
        "html_report_path": os.path.join(current_dir, "report.html")
    }

@router.post("/distributedLoadTestWithHAR/")
async def distributed_load_test_with_har(
    url: str, 
    durationInSec: str, 
    concurrentUser: str, 
    rampusers: str,
    workers: int = 1,
    har_file: UploadFile = File(...)
):
    def generate_locustfile_from_har(har_file_path: str):
        locustfile_path = "locustfile.py"
        try:
            result = subprocess.run(
                ["har2locust", har_file_path],
                capture_output=True,
                text=True,
                check=True
            )
            with open(locustfile_path, "w") as locustfile:
                locustfile.write(result.stdout)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error generating Locust file from HAR: {str(e)}")
        return locustfile_path

    # Save the uploaded HAR file
    har_file_path = "har_file.har"
    try:
        with open(har_file_path, "wb") as buffer:
            buffer.write(await har_file.read())
    except Exception as e:
        return {"error": f"Failed to save HAR file: {str(e)}"}

    locustfile_path = generate_locustfile_from_har(har_file_path)
    time.sleep(10)  # Ensure the Locustfile is properly written

    current_dir = os.getcwd().replace("\\", "/")

    try:
        subprocess.run(f"docker-compose up -d --scale locust_worker={workers}", shell=True, check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"Failed to start Docker services: {str(e)}"}

    time.sleep(5)  # Ensure containers are fully up and running

    try:
        locust_command = (
            f"docker exec locust_master locust -f /mnt/locust/locustfile.py --headless "
            f"-H {url} -r {rampusers} -t {durationInSec}s -u {concurrentUser} "
            f"--csv=/mnt/locust/locust_report --html=/mnt/locust/report.html"
        )
        print(f"Executing command: {locust_command}")  # Log command for debugging
        subprocess.run(locust_command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        return {"error": f"An error occurred during the load test: {str(e)}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}

    time.sleep(30)  # Additional delay to ensure reports are written

    summary_stats = {"stats": [], "failures": []}

    try:
        with open("locust_report_stats.csv", "r") as stats_file:
            reader = csv.DictReader(stats_file)
            for row in reader:
                summary_stats["stats"].append(row)
    except FileNotFoundError as e:
        return {"error": "Failed to read Locust stats CSV report", "details": str(e)}

    try:
        with open("locust_report_failures.csv", "r") as failures_file:
            reader = csv.DictReader(failures_file)
            for row in reader:
                summary_stats["failures"].append(row)
    except FileNotFoundError as e:
        return {"error": "Failed to read Locust failures CSV report", "details": str(e)}

    json_object = json.dumps(summary_stats, indent=4)

    with open("report.json", "w") as outfile:
        outfile.write(json_object)
    
    subprocess.run(f"docker-compose down", shell=True, check=True)
    
    return {
        "Url": url,
        "DurationInSec": durationInSec,
        "ConcurrentUser": concurrentUser,
        "Message": "Load test completed successfully, reports generated.",
        "json_report": summary_stats,
        "html_report_path": os.path.join(current_dir, "report.html")
    }

@router.get("/HTMLReport/{file_path:path}")
def download_html_report(file_path: str):
    file_path = f"./{file_path}.html"  # Adjust path as needed
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
        return Response(content=file_content, media_type="text/html", headers={"Content-Disposition": f"attachment; filename={file_path}"})
    except FileNotFoundError:
        return {"error": "File not found"}

@router.get("/JSON_Report/{file_path:path}")
def download_json_report(file_path: str):
    file_path = f"./{file_path}.json"  # Adjust path as needed
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
        return Response(content=file_content, media_type="application/json", headers={"Content-Disposition": f"attachment; filename={file_path}"})
    except FileNotFoundError:
        return {"error": "File not found"}
    
app.include_router(router)
