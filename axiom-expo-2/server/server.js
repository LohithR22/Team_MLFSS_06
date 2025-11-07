
console.log('Starting server setup...');

try {
  const express = require('express');
  const sqlite3 = require('sqlite3').verbose();
  const cors = require('cors');
  const path = require('path');
  const fs = require('fs');
  const { spawn } = require('child_process');
  const multer = require('multer');

  console.log('Dependencies loaded.');

  const app = express();
  const port = 3000;

  app.use(cors());
  app.use(express.json()); // Use express.json() instead of bodyParser.json()

  console.log('Express app configured.');

  // Create a new database file
  console.log('Connecting to database...');
  const db = new sqlite3.Database('axiom.db', (err) => {
    if (err) {
      console.error('Error connecting to database:', err.message);
      process.exit(1); // Exit if we can't connect to the DB
    }
    console.log('Connected to the SQLite database.');
  });

  // Create a users table if it doesn't exist
  db.serialize(() => {
    db.run('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, password TEXT, address TEXT, phone TEXT)', (err) => {
      if (err) {
        console.error('Error creating users table:', err.message);
      } else {
        console.log('Users table created or already exists.');
      }
    });

    // Add phone column if it doesn't exist (for existing databases)
    db.run('ALTER TABLE users ADD COLUMN phone TEXT', (err) => {
      // Ignore error if column already exists
      if (err && !err.message.includes('duplicate column')) {
        console.error('Error adding phone column:', err.message);
      }
    });
  });

  // Ensure upload and results directories exist
  const uploadsDir = path.join(__dirname, 'uploads');
  const resultsDir = path.join(__dirname, 'ocr_results');

  try {
    if (!fs.existsSync(uploadsDir)) {
      fs.mkdirSync(uploadsDir);
      console.log('Created uploads directory.');
    }
    if (!fs.existsSync(resultsDir)) {
      fs.mkdirSync(resultsDir);
      console.log('Created ocr_results directory.');
    }
  } catch (err) {
    console.error('Error creating directories:', err);
  }


  // Configure multer for image uploads
  const storage = multer.diskStorage({
    destination: function (req, file, cb) {
      cb(null, uploadsDir);
    },
    filename: function (req, file, cb) {
      const ext = path.extname(file.originalname) || '.jpg';
      const base = path.basename(file.originalname, ext).replace(/[^a-zA-Z0-9_-]/g, '_');
      const name = `${base}_${Date.now()}${ext}`;
      cb(null, name);
    }
  });
  const upload = multer({ storage });

  console.log('Multer configured.');

  app.post('/register', (req, res) => {
    const { name, password, address, phone } = req.body;

    if (!name || !password || !address) {
      return res.status(400).json({ error: 'Name, password and address are required.' });
    }

    db.get('SELECT * FROM users WHERE name = ?', [name], (err, row) => {
      if (err) {
        return res.status(500).json({ error: err.message });
      }

      if (row) {
        return res.status(400).json({ error: 'User already exists.' });
      }

      db.run('INSERT INTO users (name, password, address, phone) VALUES (?, ?, ?, ?)', [name, password, address, phone || null], function (err) {
        if (err) {
          return res.status(500).json({ error: err.message });
        }

        res.status(201).json({ message: 'User registered successfully.' });
      });
    });
  });

  app.post('/login', (req, res) => {
    const { name, password } = req.body;

    if (!name || !password) {
      return res.status(400).json({ error: 'Name and password are required.' });
    }

    db.get('SELECT * FROM users WHERE name = ? AND password = ?', [name, password], (err, row) => {
      if (err) {
        return res.status(500).json({ error: err.message });
      }

      if (row) {
        // Return user data including phone number
        res.status(200).json({
          message: 'Logged in successfully.',
          user: {
            id: row.id,
            name: row.name,
            address: row.address,
            phone: row.phone
          }
        });
      } else {
        res.status(401).json({ error: 'Invalid credentials.' });
      }
    });
  });

  // Update user phone number endpoint
  app.post('/update-phone', (req, res) => {
    const { name, phone } = req.body;

    if (!name) {
      return res.status(400).json({ error: 'Name is required.' });
    }

    if (!phone) {
      return res.status(400).json({ error: 'Phone number is required.' });
    }

    db.run('UPDATE users SET phone = ? WHERE name = ?', [phone, name], function (err) {
      if (err) {
        return res.status(500).json({ error: err.message });
      }

      if (this.changes === 0) {
        return res.status(404).json({ error: 'User not found.' });
      }

      res.status(200).json({ message: 'Phone number updated successfully.' });
    });
  });
  app.post('/ocr/upload', upload.single('image'), (req, res) => {
    try {
      if (!req.file) {
        return res.status(400).json({ error: 'Image file is required (field name: image).' });
      }

      const imagePath = req.file.path; // absolute path to uploaded file

      // Invoke Python OCR script: args => [imagePath, resultsDir]
      const pythonPath = process.env.PYTHON_PATH || 'python';
      const scriptPath = path.join(__dirname, 'ocr.py');

      const proc = spawn(pythonPath, [scriptPath, imagePath, resultsDir], { cwd: __dirname });

      let stdoutData = '';
      let stderrData = '';

      proc.stdout.on('data', (data) => {
        const chunk = data.toString();
        stdoutData += chunk;
        console.log('[OCR stdout]', chunk.trim());
      });
      proc.stderr.on('data', (data) => {
        const chunk = data.toString();
        stderrData += chunk;
        console.error('[OCR stderr]', chunk.trim());
      });

      proc.on('close', (code) => {
        console.log('[OCR exit code]', code);
        if (code !== 0) {
          return res.status(500).json({ error: 'OCR failed', details: stderrData || stdoutData });
        }

        // Expect the script to print JSON on stdout or a path marker line
        // Try to parse stdout as JSON first; if it fails, treat stdout as file path
        let parsed = null;
        try {
          parsed = JSON.parse(stdoutData);
        } catch (e) {
          // not JSON; assume it's a file path string
        }

        if (parsed && parsed.medicines) {
          // Save a copy of JSON to resultsDir with generated name as well
          const outPath = path.join(resultsDir, `medicines_${Date.now()}.json`);
          fs.writeFileSync(outPath, JSON.stringify(parsed, null, 2), 'utf8');
          return res.status(200).json({ medicines: parsed.medicines, jsonPath: outPath });
        }

        const printed = stdoutData.trim();
        const exists = printed && fs.existsSync(printed);
        if (exists) {
          // Read JSON to return medicines quickly
          try {
            const content = JSON.parse(fs.readFileSync(printed, 'utf8'));
            return res.status(200).json({ medicines: content.medicines || [], jsonPath: printed });
          } catch (e) {
            return res.status(200).json({ jsonPath: printed });
          }
        }

        return res.status(500).json({ error: 'Unexpected OCR output', stdout: stdoutData, stderr: stderrData });
      });
    } catch (err) {
      return res.status(500).json({ error: 'Server error', details: String(err) });
    }
  });

  console.log('Routes configured.');

  // Helper: Split array into N chunks as evenly as possible
  function chunkArray(arr, n) {
    if (n <= 0 || arr.length === 0) return [];
    const chunkSize = Math.ceil(arr.length / n);
    const chunks = [];
    for (let i = 0; i < arr.length; i += chunkSize) {
      chunks.push(arr.slice(i, i + chunkSize));
    }
    return chunks;
  }

  // Helper: Run Python scraper for a single medicine and site
  async function runScraper(pythonPath, scriptPath, mode, medicine) {
    return new Promise((resolve) => {
      const proc = spawn(pythonPath, [scriptPath, mode, medicine], { cwd: __dirname });
      let stdoutData = '';
      let stderrData = '';
      proc.stdout.on('data', (d) => { stdoutData += d.toString(); });
      proc.stderr.on('data', (d) => { stderrData += d.toString(); });
      proc.on('close', () => {
        if (stderrData) {
          console.error(`[SCRAPE ${mode} stderr]`, medicine, stderrData.trim());
        }
        try {
          const parsed = JSON.parse(stdoutData);
          resolve(parsed);
        } catch (e) {
          resolve({ medicine, error: 'Failed to parse scraper output', stderr: stderrData, raw: stdoutData });
        }
      });
    });
  }

  // Scrape endpoint: accepts { medicines: string[] }
  // Uses 6 workers: 3 for Apollo, 3 for Netmed
  app.post('/scrape', async (req, res) => {
    try {
      const body = req.body || {};
      const medicines = Array.isArray(body.medicines) ? body.medicines : [];
      if (!medicines.length) {
        return res.status(400).json({ error: 'medicines array is required' });
      }

      const pythonPath = process.env.PYTHON_PATH || 'python';
      const scriptPath = path.join(__dirname, 'all_scapes.py');

      // Split medicines into 3 chunks for Apollo workers
      const apolloChunks = chunkArray(medicines, 3);
      // Split medicines into 3 chunks for Netmed workers
      const netmedChunks = chunkArray(medicines, 3);

      // Create worker tasks: 3 Apollo + 3 Netmed = 6 workers total
      const workerTasks = [];

      // Apollo workers (3 threads)
      for (let i = 0; i < apolloChunks.length; i++) {
        const chunk = apolloChunks[i];
        if (chunk.length > 0) {
          workerTasks.push(
            Promise.all(chunk.map(med => runScraper(pythonPath, scriptPath, 'apollo', med)))
              .then(results => ({ type: 'apollo', results }))
          );
        }
      }

      // Netmed workers (3 threads)
      for (let i = 0; i < netmedChunks.length; i++) {
        const chunk = netmedChunks[i];
        if (chunk.length > 0) {
          workerTasks.push(
            Promise.all(chunk.map(med => runScraper(pythonPath, scriptPath, 'netmed', med)))
              .then(results => ({ type: 'netmed', results }))
          );
        }
      }

      // Run all 6 workers in parallel
      const allResults = await Promise.all(workerTasks);

      // Combine results by medicine name
      const medicineMap = {};
      medicines.forEach(med => {
        medicineMap[med] = { medicine: med, apollo: null, netmed: null, errors: {} };
      });

      // Merge Apollo and Netmed results
      allResults.forEach(group => {
        group.results.forEach(result => {
          const med = result.medicine;
          if (medicineMap[med]) {
            if (group.type === 'apollo') {
              medicineMap[med].apollo = result.apollo;
              if (result.error) medicineMap[med].errors.apollo = result.error;
            } else if (group.type === 'netmed') {
              medicineMap[med].netmed = result.netmed;
              if (result.error) medicineMap[med].errors.netmed = result.error;
            }
          }
        });
      });

      // Convert to array and clean up empty errors
      const finalResults = Object.values(medicineMap).map(item => {
        const clean = { ...item };
        if (Object.keys(clean.errors).length === 0) {
          delete clean.errors;
        }
        return clean;
      });

      return res.status(200).json({ results: finalResults });
    } catch (err) {
      return res.status(500).json({ error: 'Scrape server error', details: String(err) });
    }
  });

  // Find pharmacies endpoint
  app.post('/find-pharmacies', async (req, res) => {
    try {
      const { source_lat, source_lon, medicine_names, top_k } = req.body;

      if (!source_lat || !source_lon) {
        return res.status(400).json({ error: 'Source coordinates (source_lat, source_lon) are required' });
      }

      if (!medicine_names || !Array.isArray(medicine_names) || medicine_names.length === 0) {
        return res.status(400).json({ error: 'medicine_names array is required and cannot be empty' });
      }

      const pythonPath = process.env.PYTHON_PATH || 'python';
      const scriptPath = path.join(__dirname, 'find_pharmacies.py');

      // Prepare arguments for Python script
      const args = [
        scriptPath,
        JSON.stringify({
          source_lat: parseFloat(source_lat),
          source_lon: parseFloat(source_lon),
          medicine_names: medicine_names,
          top_k: top_k || 5
        })
      ];

      const proc = spawn(pythonPath, args, { cwd: __dirname });
      let stdoutData = '';
      let stderrData = '';

      proc.stdout.on('data', (d) => { stdoutData += d.toString(); });
      proc.stderr.on('data', (d) => { stderrData += d.toString(); });

      await new Promise((resolve) => {
        proc.on('close', (code) => {
          console.log('[FIND_PHARMACIES exit code]', code);
          resolve();
        });
      });

      if (stderrData) {
        console.error('[FIND_PHARMACIES stderr]', stderrData.trim());
      }

      try {
        const parsed = JSON.parse(stdoutData);
        return res.status(200).json(parsed);
      } catch (e) {
        return res.status(500).json({
          error: 'Failed to parse pharmacy finder output',
          stderr: stderrData,
          raw: stdoutData
        });
      }
    } catch (err) {
      return res.status(500).json({ error: 'Find pharmacies server error', details: String(err) });
    }
  });

  // Delivery map endpoint
  app.post('/delivery-map', async (req, res) => {
    try {
      const { origin, green_stores, yellow_stores, red_stores, best_store, create_delivery, agent_idx } = req.body;

      if (!origin || !origin.latitude || !origin.longitude) {
        return res.status(400).json({ error: 'Origin coordinates (latitude, longitude) are required' });
      }

      const pythonPath = process.env.PYTHON_PATH || 'python';
      const scriptPath = path.join(__dirname, 'delivery_map.py');

      // Prepare arguments for Python script
      const mapData = {
        origin: [origin.latitude, origin.longitude],
        green_stores: green_stores || [],
        yellow_stores: yellow_stores || [],
        red_stores: red_stores || []
      };

      // If delivery is requested, include best store for assignment
      if (create_delivery && best_store && best_store.latitude && best_store.longitude) {
        mapData.best_store = [best_store.latitude, best_store.longitude];
        mapData.create_delivery = true;
        if (agent_idx !== undefined && agent_idx !== null) {
          mapData.agent_idx = agent_idx;
        }
      }

      const args = [
        scriptPath,
        JSON.stringify(mapData)
      ];

      const proc = spawn(pythonPath, args, { cwd: __dirname });
      let stdoutData = '';
      let stderrData = '';

      proc.stdout.on('data', (d) => { stdoutData += d.toString(); });
      proc.stderr.on('data', (d) => { stderrData += d.toString(); });

      await new Promise((resolve) => {
        proc.on('close', () => resolve());
      });

      if (stderrData) {
        console.error('[DELIVERY_MAP stderr]', stderrData.trim());
      }

      try {
        const parsed = JSON.parse(stdoutData);
        return res.status(200).json(parsed);
      } catch (e) {
        return res.status(500).json({
          error: 'Failed to parse delivery map output',
          stderr: stderrData,
          raw: stdoutData
        });
      }
    } catch (err) {
      return res.status(500).json({ error: 'Delivery map server error', details: String(err) });
    }
  });

  // HWC Report endpoint
  // Jan Aushadhi lookup endpoint
  app.post('/janaushadhi-lookup', async (req, res) => {
    try {
      const { medicine_names } = req.body;

      if (!medicine_names || !Array.isArray(medicine_names) || medicine_names.length === 0) {
        return res.status(400).json({ error: 'medicine_names array is required and cannot be empty' });
      }

      const pythonPath = process.env.PYTHON_PATH || 'python';
      const scriptPath = path.join(__dirname, 'janaushadhi_api.py');

      // Prepare arguments for Python script
      const args = [
        scriptPath,
        JSON.stringify(medicine_names)
      ];

      const proc = spawn(pythonPath, args, { cwd: __dirname });
      let stdoutData = '';
      let stderrData = '';

      proc.stdout.on('data', (d) => { stdoutData += d.toString(); });
      proc.stderr.on('data', (d) => { stderrData += d.toString(); });

      await new Promise((resolve) => {
        proc.on('close', (code) => {
          console.log('[JANAUSHADHI exit code]', code);
          resolve();
        });
      });

      if (stderrData) {
        console.error('[JANAUSHADHI stderr]', stderrData.trim());
      }

      try {
        const parsed = JSON.parse(stdoutData);
        return res.status(200).json(parsed);
      } catch (e) {
        return res.status(500).json({
          error: 'Failed to parse Jan Aushadhi lookup output',
          stderr: stderrData,
          raw: stdoutData
        });
      }
    } catch (err) {
      return res.status(500).json({ error: 'Jan Aushadhi lookup server error', details: String(err) });
    }
  });

  app.get('/hwc-report', (req, res) => {
    try {
      const reportPath = path.join(__dirname, 'hwc_report.json');
      if (!fs.existsSync(reportPath)) {
        return res.status(404).json({ error: 'HWC report file not found' });
      }
      const reportData = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
      return res.status(200).json(reportData);
    } catch (err) {
      return res.status(500).json({ error: 'Failed to load HWC report', details: String(err) });
    }
  });

  app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
  });

} catch (error) {
  console.error('Failed to start server:', error);
  process.exit(1);
}
