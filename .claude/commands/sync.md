---
description: Sync remote system with latest code and rebuild
---

Synchronize the remote system (oci-opc) with the latest repository changes and rebuild the project.

**Steps:**
1. SSH to remote system
2. Pull latest changes from GitHub
3. Rebuild the Java project with Maven

Execute the following commands:

```bash
# Pull latest changes and rebuild on remote system
ssh oci-opc "cd BSON-JSON-bakeoff && git pull origin main && mvn clean package"
```

**What this does:**
- Connects to remote system (oci-opc)
- Navigates to project directory
- Pulls latest code from GitHub main branch
- Rebuilds the JAR file: `target/insertTest-1.0-jar-with-dependencies.jar`

**Expected output:**
- Git pull summary showing updated files
- Maven build progress
- BUILD SUCCESS message
- JAR file location confirmation

**Build time:** Approximately 30-60 seconds

**Common issues:**
- If build fails due to stale dependencies: Add `-U` flag to force update
- If git conflicts exist: Manual resolution required
- If remote has uncommitted changes: Stash or commit them first
