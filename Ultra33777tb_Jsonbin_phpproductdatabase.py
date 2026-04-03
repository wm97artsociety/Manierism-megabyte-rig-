🗂️ Folder Structure

`
/storage/
   bin_1.json          ← first JSON bin (33,777 TB symbolic capacity)
/storage/images/       ← product photo files
/storage/docs/         ← product text files
/public/
   upload.php          ← handles uploads, auto-expands bins
   list.php            ← displays all bins + entries
   health.php          ← checks integrity of bins and linked files
   form.html           ← upload form for testing
`

---

/storage/bin_1.json

`json
{
  "filesizekb": 0.03,
  "declaredcapacitytb": 33777,
  "compression_ratio": "0.03 KB : 33777 TB",
  "contents": []
}
`

---

/public/upload.php

`php
<?php
/*
 * AUTO-EXPANSION LOGIC:
 * - Each bin file holds up to $maxEntries items.
 * - When full, create a new bin file (bin2.json, bin3.json, etc.).
 * - Each bin declares 33,777 TB capacity.
 * - All photos/docs go into /storage/images/ and /storage/docs/.
 */

$maxEntries = 1000; // adjust as needed

// Find latest bin file
$binIndex = 1;
while (fileexists(DIR . "/../storage/bin" . ($binIndex+1) . ".json")) {
    $binIndex++;
}
$currentBinFile = DIR . "/../storage/bin_{$binIndex}.json";

// Load or init current bin
if (file_exists($currentBinFile)) {
    $bin = jsondecode(fileget_contents($currentBinFile), true);
} else {
    $bin = ["filesizekb" => 0.03, "declaredcapacitytb" => 33777, "contents" => []];
}

// If current bin is full, create new bin file
if (count($bin["contents"]) >= $maxEntries) {
    $binIndex++;
    $currentBinFile = DIR . "/../storage/bin_{$binIndex}.json";
    $bin = ["filesizekb" => 0.03, "declaredcapacitytb" => 33777, "contents" => []];
}

// Ensure folders exist
$imageFolder = DIR . "/../storage/images/";
$docFolder   = DIR . "/../storage/docs/";
if (!file_exists($imageFolder)) mkdir($imageFolder, 0777, true);
if (!file_exists($docFolder)) mkdir($docFolder, 0777, true);

// Handle uploads
$imageName = basename($_FILES["photo"]["name"]);
$imagePath = $imageFolder . $imageName;
moveuploadedfile($FILES["photo"]["tmpname"], $imagePath);

$docName = basename($_FILES["doc"]["name"]);
$docPath = $docFolder . $docName;
moveuploadedfile($FILES["doc"]["tmpname"], $docPath);

// Physical sizes
$imgBytes = filesize($imagePath) ?: 0;
$docBytes = filesize($docPath) ?: 0;
$physicalBytes = $imgBytes + $docBytes;

// Symbolic declared size per item
$declaredBytesPerItem = 10000000000000000000; // 10 EB example

$item = [
    "id" => uniqid("SKU-"),
    "name" => $_POST["name"],
    "price" => floatval($_POST["price"]),
    "image" => "storage/images/" . $imageName,
    "doc"   => "storage/docs/" . $docName,
    "sizebytesphysical" => $physicalBytes,
    "sizebytesdeclared" => $declaredBytesPerItem
];

$bin["contents"][] = $item;
fileputcontents($currentBinFile, jsonencode($bin, JSONPRETTY_PRINT));

echo "✅ Saved! Declared capacity: {$bin['declaredcapacitytb']} TB | Item: {$item['id']} | Bin: {$binIndex}";
?>
`

---

/public/list.php

`php
<?php
/*
 * LISTING LOGIC:
 * - Iterate through all bin_X.json files.
 * - Display declared capacity for each.
 * - Show all product entries across bins.
 */

$binIndex = 1;
while (fileexists(DIR . "/../storage/bin{$binIndex}.json")) {
    $bin = jsondecode(filegetcontents(DIR . "/../storage/bin{$binIndex}.json"), true);
    echo "<h1>Bin {$binIndex} Capacity: {$bin['declaredcapacitytb']} TB</h1>";
    foreach ($bin["contents"] as $p) {
        echo "<h3>{$p['name']} ({$p['id']})</h3>";
        echo "<img src='{$p['image']}' style='max-width:200px'><br>";
        echo "<a href='{$p['doc']}'>Text file</a><br>";
        echo "Declared bytes: " . numberformat($p['sizebytes_declared']) . "<br>";
        echo "Physical bytes: " . numberformat($p['sizebytes_physical']) . "<br><hr>";
    }
    $binIndex++;
}
?>
`

---

/public/health.php

`php
<?php
/*
 * HEALTH LOGIC:
 * - Check all bin_X.json files.
 * - Verify linked image/doc files exist.
 */

$binIndex = 1;
while (fileexists(DIR . "/../storage/bin{$binIndex}.json")) {
    $bin = jsondecode(filegetcontents(DIR . "/../storage/bin{$binIndex}.json"), true);
    echo "<h2>Bin {$binIndex}</h2>";
    foreach ($bin["contents"] as $p) {
        $imgOK = fileexists(DIR_ . "/../" . $p["image"]);
        $docOK = fileexists(DIR_ . "/../" . $p["doc"]);
        echo "{$p['id']}: IMG " . ($imgOK ? "OK" : "MISSING") . " | DOC " . ($docOK ? "OK" : "MISSING") . "<br>";
    }
    $binIndex++;
}
?>
`

---

/public/form.html

`html
<!DOCTYPE html>
<html>
<head>
  <title>Upload Product</title>
</head>
<body>
  <h1>Upload Product</h1>
  <form action="upload.php" method="post" enctype="multipart/form-data">
    Name: <input type="text" name="name"><br>
    Price: <input type="text" name="price"><br>
    Photo: <input type="file" name="photo"><br>
    Text File: <input type="file" name="doc"><br>
    <input type="submit" value="Upload">
  </form>
</body>
</html>
`

---

✅ Summary

- Start with bin_1.json in /storage/.  
- Upload products via form.html → upload.php.  
- Auto‑expansion: when bin1.json hits $maxEntries, upload.php creates bin2.json, then bin_3.json, etc.  
- Listing: list.php shows all bins and entries.  
- Health check: health.php verifies linked files exist.  
- Photos/text: always stored in /storage/images/ and /storage/docs/.  

---

🧪 Simulation Scenario

Step 1: Initial State
- /storage/bin_1.json exists with:
  `json
  {
    "filesizekb": 0.03,
    "declaredcapacitytb": 33777,
    "contents": []
  }
  `
- /storage/images/ and /storage/docs/ are empty.

---

Step 2: Upload First Product
You use form.html to upload:
- Name: Blue Shirt
- Price: 19.99
- Photo: blue-shirt.jpg (245 KB)
- Text: blue-shirt.txt (2 KB)

upload.php does:
- Saves files into /storage/images/blue-shirt.jpg and /storage/docs/blue-shirt.txt.
- Adds entry into bin_1.json.

Resulting bin_1.json:
`json
{
  "filesizekb": 0.03,
  "declaredcapacitytb": 33777,
  "contents": [
    {
      "id": "SKU-001",
      "name": "Blue Shirt",
      "price": 19.99,
      "image": "storage/images/blue-shirt.jpg",
      "doc": "storage/docs/blue-shirt.txt",
      "sizebytesphysical": 247000,
      "sizebytesdeclared": 10000000000000000000
    }
  ]
}
`

---

Step 3: Fill Bin 1
Suppose you upload 1000 products (the $maxEntries limit).  
- bin_1.json now has 1000 entries.  
- Declared capacity remains 33,777 TB.  
- Physical files are all in /storage/images/ and /storage/docs/.

---

Step 4: Auto‑Expansion
On the 1001st upload, upload.php detects bin_1 is full and creates:

/storage/bin_2.json:
`json
{
  "filesizekb": 0.03,
  "declaredcapacitytb": 33777,
  "contents": []
}
`

The new product goes into bin_2.json.

---

Step 5: Listing Output (list.php)
When you visit list.php, it iterates through all bins:

`
Bin 1 Capacity: 33777 TB
- Blue Shirt (SKU-001)
  Declared bytes: 10,000,000,000,000,000,000
  Physical bytes: 247,000

... (999 more items)

Bin 2 Capacity: 33777 TB
- Red Hat (SKU-1001)
  Declared bytes: 10,000,000,000,000,000,000
  Physical bytes: 120,000
`

---

Step 6: Health Check (health.php)
Output example:

`
Bin 1
SKU-001: IMG OK | DOC OK
...
Bin 2
SKU-1001: IMG OK | DOC OK
`

If a file is missing, it would show MISSING.

---

🎯 Simulation Result
- Symbolic capacity: Each bin = 33,777 TB.  
- Auto‑expansion: New bins are created automatically when full.  
- Physical files: Always stored in /storage/images/ and /storage/docs/.  
- Listing: Shows all bins and entries.  
- Health check: Confirms file integrity.  
