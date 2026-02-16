#!/usr/bin/env python3
"""
Version detection module for databases, Docker images, and client libraries.
"""

import subprocess
import re
import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

def get_docker_image_version(image_name: str, container_name: Optional[str] = None) -> Dict[str, str]:
    """
    Get Docker image version/tag information.
    
    Args:
        image_name: Docker image name (e.g., "mongo", "documentdb-local")
        container_name: Optional container name to get running container's image
        
    Returns:
        Dictionary with 'image', 'tag', 'image_id', and 'digest' if available
    """
    result = {
        "image": image_name,
        "tag": "latest",  # default
        "image_id": "",
        "digest": ""
    }
    
    try:
        # If container name provided, get image from running container
        if container_name:
            cmd = f"docker inspect {container_name} --format '{{{{.Image}}}}'"
            inspect_result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
            if inspect_result.returncode == 0:
                image_id = inspect_result.stdout.strip()
                result["image_id"] = image_id
                
                # Get image tag from image ID
                cmd = f"docker images --format '{{{{.Repository}}}}:{{{{.Tag}}}}' --filter 'dangling=false'"
                images_result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
                if images_result.returncode == 0:
                    for line in images_result.stdout.strip().split('\n'):
                        if image_name in line:
                            # Extract tag
                            if ':' in line:
                                parts = line.split(':')
                                if len(parts) >= 2:
                                    result["tag"] = parts[-1]
                            break
        
        # Get image information directly
        cmd = f"docker images {image_name} --format '{{{{.Repository}}}}:{{{{.Tag}}}} {{{{.ID}}}}'"
        images_result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        if images_result.returncode == 0 and images_result.stdout.strip():
            lines = images_result.stdout.strip().split('\n')
            if lines:
                # Get first (most recent) image
                parts = lines[0].split()
                if len(parts) >= 2:
                    repo_tag = parts[0]
                    if ':' in repo_tag:
                        result["tag"] = repo_tag.split(':')[1]
                    result["image_id"] = parts[1]
        
        # Try to get digest if available
        cmd = f"docker images {image_name} --format '{{{{.Digest}}}}'"
        digest_result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        if digest_result.returncode == 0 and digest_result.stdout.strip():
            digest = digest_result.stdout.strip().split('\n')[0]
            if digest and digest != '<none>':
                result["digest"] = digest
                
    except Exception as e:
        logger.warning(f"Failed to get Docker image version for {image_name}: {e}")
    
    return result


def get_database_version(db_type: str, connection_info: Dict[str, Any]) -> Optional[str]:
    """
    Query database for its version.
    
    Args:
        db_type: Database type ("mongodb", "documentdb", "postgresql", "oracle", "cockroachdb", "yugabytedb")
        connection_info: Connection information (host, port, etc.)
        
    Returns:
        Database version string or None if failed
    """
    try:
        if db_type in ["mongodb", "documentdb", "mongodb-cloud", "documentdb-azure"]:
            return _get_mongodb_version(connection_info)
        elif db_type == "postgresql":
            return _get_postgresql_version(connection_info)
        elif db_type == "oracle":
            return _get_oracle_version(connection_info)
        elif db_type == "cockroachdb":
            return _get_cockroachdb_version(connection_info)
        elif db_type == "yugabytedb":
            return _get_yugabytedb_version(connection_info)
        else:
            logger.warning(f"Unknown database type: {db_type}")
            return None
    except Exception as e:
        logger.warning(f"Failed to get database version for {db_type}: {e}")
        return None


def _get_mongodb_version(connection_info: Dict[str, Any]) -> Optional[str]:
    """Get MongoDB/DocumentDB version."""
    try:
        host = connection_info.get('host', 'localhost')
        port = connection_info.get('port', 27017)
        user = connection_info.get('user')
        password = connection_info.get('password')
        database = connection_info.get('database', 'admin')

        # Try using pymongo first (more reliable, works without mongosh)
        try:
            from pymongo import MongoClient
            import urllib.parse

            # Use full connection string if provided (e.g. cloud databases)
            if connection_info.get('connection_string'):
                connection_uri = connection_info['connection_string']
            elif user and password:
                encoded_password = urllib.parse.quote(password, safe='')
                connection_uri = f"mongodb://{user}:{encoded_password}@{host}:{port}/{database}"
            else:
                connection_uri = f"mongodb://{host}:{port}/{database}"

            # Connect and get version
            client = MongoClient(connection_uri, serverSelectionTimeoutMS=5000)
            # Try buildInfo first (standard MongoDB command)
            try:
                version_info = client.admin.command('buildInfo')
                if version_info and 'version' in version_info:
                    version = version_info['version']
                    client.close()
                    return version
            except Exception:
                # buildInfo might not be supported, try db.version() instead
                pass
            
            # Fallback: try db.version() method (what mongosh uses)
            try:
                db = client.get_database(database if database else 'admin')
                version = db.command('eval', 'db.version()')
                if version:
                    # version might be a dict with 'retval' key
                    if isinstance(version, dict) and 'retval' in version:
                        version = version['retval']
                    client.close()
                    return str(version).strip('"\'')
            except Exception:
                pass
            
            client.close()
        except ImportError:
            # pymongo not available, fall back to mongosh
            pass
        except Exception as e:
            logger.debug(f"pymongo connection failed, trying mongosh: {e}")
        
        # Fallback: Try using mongosh if available
        if user and password:
            # Use connection URI format for authentication
            import urllib.parse
            encoded_password = urllib.parse.quote(password, safe='')
            connection_uri = f"mongodb://{user}:{encoded_password}@{host}:{port}/{database}"
            cmd = f"mongosh --quiet '{connection_uri}' --eval 'db.version()'"
        else:
            # No authentication
            cmd = f"mongosh --quiet --host {host} --port {port} --eval 'db.version()'"
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            version = result.stdout.strip()
            # Remove quotes if present
            version = version.strip('"\'')
            if version:  # Only return if we got a non-empty version
                return version
        
        # Fallback: try docker exec if container name provided (only for MongoDB, not DocumentDB)
        # DocumentDB containers don't have mongosh installed
        container = connection_info.get('container')
        if container and not user:  # Only use docker exec for MongoDB (no auth)
            cmd = f"docker exec {container} mongosh --quiet --eval 'db.version()'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip().strip('"\'')
                if version:
                    return version
    except Exception as e:
        logger.warning(f"Failed to get MongoDB/DocumentDB version: {e}")
    return None


def _get_postgresql_version(connection_info: Dict[str, Any]) -> Optional[str]:
    """Get PostgreSQL version."""
    try:
        host = connection_info.get('host', 'localhost')
        port = connection_info.get('port', 5432)
        user = connection_info.get('user', 'postgres')
        password = connection_info.get('password', '')
        
        # Try psql command
        env = os.environ.copy()
        if password:
            env['PGPASSWORD'] = password
        
        cmd = f"psql -h {host} -p {port} -U {user} -t -c 'SELECT version();'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, env=env)
        if result.returncode == 0:
            version = result.stdout.strip()
            # Extract version number (e.g., "PostgreSQL 17.1")
            match = re.search(r'PostgreSQL\s+([\d.]+)', version)
            if match:
                return match.group(1)
            return version
        
        # Fallback: docker exec
        container = connection_info.get('container')
        if container:
            cmd = f"docker exec {container} psql -U {user} -t -c 'SELECT version();'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version = result.stdout.strip()
                match = re.search(r'PostgreSQL\s+([\d.]+)', version)
                if match:
                    return match.group(1)
                return version
    except Exception as e:
        logger.warning(f"Failed to get PostgreSQL version: {e}")
    return None


def _get_oracle_version(connection_info: Dict[str, Any]) -> Optional[str]:
    """Get Oracle version."""
    try:
        # Oracle version is typically queried via JDBC in the Java code
        # For Python, we'd need cx_Oracle or similar
        # For now, return None and let Java code handle it
        logger.info("Oracle version detection should be done via Java/JDBC")
        return None
    except Exception as e:
        logger.warning(f"Failed to get Oracle version: {e}")
    return None


def _get_cockroachdb_version(connection_info: Dict[str, Any]) -> Optional[str]:
    """Get CockroachDB version."""
    try:
        container = connection_info.get('container')

        # Primary: docker exec cockroach version
        if container:
            cmd = f"docker exec {container} cockroach version"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Parse output like "Build Tag:    v24.3.1" or "cockroach v24.3.1"
                match = re.search(r'v(\d+\.\d+(?:\.\d+)?)', result.stdout)
                if match:
                    return match.group(1)

        # Fallback: SQL query via cockroach sql --insecure
        if container:
            cmd = f"docker exec {container} cockroach sql --insecure -e \"SELECT version()\""
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Parse CockroachDB version from SELECT version() output
                match = re.search(r'v(\d+\.\d+(?:\.\d+)?)', result.stdout)
                if match:
                    return match.group(1)

        # Final fallback: psql from host
        host = connection_info.get('host', 'localhost')
        port = connection_info.get('port', 26257)
        user = connection_info.get('user', 'root')
        password = connection_info.get('password', '')

        env = os.environ.copy()
        if password:
            env['PGPASSWORD'] = password

        cmd = f"psql -h {host} -p {port} -U {user} -t -c \'SELECT version();\'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10, env=env)
        if result.returncode == 0:
            match = re.search(r'v(\d+\.\d+(?:\.\d+)?)', result.stdout)
            if match:
                return match.group(1)

    except Exception as e:
        logger.warning(f"Failed to get CockroachDB version: {e}")
    return None


def _get_yugabytedb_version(connection_info: Dict[str, Any]) -> Optional[str]:
    """Get YugabyteDB version."""
    try:
        container = connection_info.get('container')

        # Primary: docker exec yugabyted version
        if container:
            cmd = f"docker exec {container} yugabyted version"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Parse output like "yugabyted YB-2.23.1.0-b0"
                match = re.search(r'YB-(\d+\.\d+(?:\.\d+(?:\.\d+)?)?)', result.stdout)
                if match:
                    return match.group(1)

        # Fallback: docker exec yb-admin --version
        if container:
            cmd = f"docker exec {container} yb-admin --version"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                match = re.search(r'(\d+\.\d+(?:\.\d+(?:\.\d+)?)?)', result.stdout)
                if match:
                    return match.group(1)

        # Final fallback: ysqlsh with resolved hostname
        # YugabyteDB binds YSQL to container hostname, not localhost
        if container:
            # Resolve hostname inside container
            hostname_cmd = f"docker exec {container} hostname"
            hostname_result = subprocess.run(hostname_cmd, shell=True, capture_output=True, text=True, timeout=5)
            if hostname_result.returncode == 0:
                yb_host = hostname_result.stdout.strip()
                cmd = f"docker exec {container} ysqlsh -h {yb_host} -U yugabyte -t -c \'SELECT version();\'"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    # Parse "PostgreSQL 11.2-YB-2.23.1.0-b0" style output
                    match = re.search(r'YB-(\d+\.\d+(?:\.\d+(?:\.\d+)?)?)', result.stdout)
                    if match:
                        return match.group(1)

    except Exception as e:
        logger.warning(f"Failed to get YugabyteDB version: {e}")
    return None


def get_client_library_version(library_name: str) -> Optional[str]:
    """
    Get Java client library version from pom.xml or JAR manifest.
    
    Args:
        library_name: Library name (e.g., "mongodb-driver-sync", "ojdbc11", "postgresql")
        
    Returns:
        Version string or None if not found
    """
    try:
        # First try pom.xml
        pom_path = Path(__file__).parent.parent / "pom.xml"
        if pom_path.exists():
            version = _get_version_from_pom(pom_path, library_name)
            if version:
                return version
        
        # Try JAR manifest
        jar_path = Path(__file__).parent.parent / "target" / "insertTest-1.0-jar-with-dependencies.jar"
        if jar_path.exists():
            version = _get_version_from_jar(jar_path, library_name)
            if version:
                return version
        
        logger.warning(f"Could not find version for library: {library_name}")
        return None
    except Exception as e:
        logger.warning(f"Failed to get client library version for {library_name}: {e}")
        return None


def _get_version_from_pom(pom_path: Path, library_name: str) -> Optional[str]:
    """Extract version from pom.xml."""
    try:
        tree = ET.parse(pom_path)
        root = tree.getroot()
        
        # Map library names to Maven artifact IDs
        artifact_map = {
            "mongodb-driver-sync": "mongodb-driver-sync",
            "ojdbc11": "ojdbc11",
            "postgresql": "postgresql"
        }
        
        artifact_id = artifact_map.get(library_name, library_name)
        
        # Find dependency with matching artifactId
        # Handle default namespace
        ns = {'maven': 'http://maven.apache.org/POM/4.0.0'}
        if root.tag.startswith('{'):
            # Has namespace
            for dep in root.findall('.//maven:dependency', ns):
                artifact_elem = dep.find('maven:artifactId', ns)
                if artifact_elem is not None and artifact_elem.text == artifact_id:
                    version_elem = dep.find('maven:version', ns)
                    if version_elem is not None:
                        return version_elem.text
        else:
            # No namespace
            for dep in root.findall('.//dependency'):
                artifact_elem = dep.find('artifactId')
                if artifact_elem is not None and artifact_elem.text == artifact_id:
                    version_elem = dep.find('version')
                    if version_elem is not None:
                        return version_elem.text
    except Exception as e:
        logger.warning(f"Failed to parse pom.xml: {e}")
    return None


def _get_version_from_jar(jar_path: Path, library_name: str) -> Optional[str]:
    """Extract version from JAR manifest (simplified - would need to extract JAR)."""
    # This is complex - would need to extract JAR and read MANIFEST.MF
    # For now, return None and rely on pom.xml
    return None


def get_java_version() -> Optional[str]:
    """Get Java runtime version."""
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 or result.stderr:
            # Java version is in stderr
            version_output = result.stderr
            # Extract version (e.g., "openjdk version "11.0.1"")
            match = re.search(r'version\s+"?([\d.]+)', version_output)
            if match:
                return match.group(1)
    except Exception as e:
        logger.warning(f"Failed to get Java version: {e}")
    return None


def get_all_versions(db_type: str, image_name: str, container_name: Optional[str] = None,
                    connection_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get all version information for a database test.
    
    Args:
        db_type: Database type
        image_name: Docker image name
        container_name: Container name
        connection_info: Database connection information
        
    Returns:
        Dictionary with all version information
    """
    versions = {
        "database": {
            "type": db_type,
            "version": None,
            "docker_image": image_name,
            "docker_image_tag": "latest",
            "docker_image_id": ""
        },
        "client": {
            "library": None,
            "version": None
        },
        "java_version": None
    }
    
    # Get Docker image info
    docker_info = get_docker_image_version(image_name, container_name)
    versions["database"]["docker_image_tag"] = docker_info.get("tag", "latest")
    versions["database"]["docker_image_id"] = docker_info.get("image_id", "")
    
    # Get database version
    if connection_info:
        db_version = get_database_version(db_type, connection_info)
        # For DocumentDB, if direct connection fails, try to extract version from image tag
        if not db_version and db_type == "documentdb" and docker_info.get("tag"):
            # DocumentDB image tags often contain version info
            tag = docker_info.get("tag", "")
            # Try to extract version from tag (e.g., "1.0.0" or "v1.0.0")
            import re
            version_match = re.search(r'v?(\d+\.\d+(?:\.\d+)?)', tag)
            if version_match:
                db_version = version_match.group(1)
        versions["database"]["version"] = db_version
    
    # Get client library version
    client_lib_map = {
        "mongodb": "mongodb-driver-sync",
        "documentdb": "mongodb-driver-sync",
        "mongodb-cloud": "mongodb-driver-sync",
        "documentdb-azure": "mongodb-driver-sync",
        "postgresql": "postgresql",
        "yugabytedb": "postgresql",
        "cockroachdb": "postgresql",
        "oracle": "ojdbc11"
    }
    client_lib = client_lib_map.get(db_type)
    if client_lib:
        versions["client"]["library"] = client_lib
        versions["client"]["version"] = get_client_library_version(client_lib)
    
    # Get Java version
    versions["java_version"] = get_java_version()
    
    return versions
