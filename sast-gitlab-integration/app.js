const express = require('express');
const app = express();
const bodyParser = require('body-parser');
const fs = require('fs');
const bcrypt = require('bcrypt');
const { exec } = require('child_process');

// Example of insecure user input handling leading to Command Injection vulnerability
app.use(bodyParser.json());

// Vulnerable to SQL Injection: Directly using user input without sanitization
app.post('/login', (req, res) => {
    const username = req.body.username;
    const password = req.body.password;
    
    // Unsafe SQL query concatenation - vulnerable to SQL Injection
    const query = `SELECT * FROM users WHERE username='${username}' AND password='${password}'`;

    // Imagine this query is sent to the database...
    db.query(query, (err, result) => {
        if (err) {
            res.status(500).send('Error');
        } else if (result.length > 0) {
            res.status(200).send('Login successful');
        } else {
            res.status(401).send('Invalid credentials');
        }
    });
});

// Hardcoded sensitive information (API key) exposed in the code
const apiKey = '12345-abcde';

// Insecure cookie handling without secure flags
app.get('/profile', (req, res) => {
    const userId = req.cookies.userId; // Retrieving userId from cookies
    
    // Vulnerable to session hijacking - cookie should be set with Secure and HttpOnly flags
    res.cookie('userId', userId);
    res.send('User profile');
});

// Vulnerable to Command Injection: exec() with unsanitized input
app.get('/run-script', (req, res) => {
    const userCommand = req.query.cmd;
    
    // Dangerous to execute arbitrary commands from user input
    exec(userCommand, (error, stdout, stderr) => {
        if (error) {
            res.status(500).send('Error');
        } else {
            res.send(stdout);
        }
    });
});

// File inclusion vulnerability
app.get('/read-file', (req, res) => {
    const filename = req.query.filename;
    
    // File inclusion vulnerability
    fs.readFile(filename, 'utf8', (err, data) => {
        if (err) {
            res.status(500).send('Error reading file');
        } else {
            res.send(data);
        }
    });
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
