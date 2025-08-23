## 📋 Complete Input Flow Summary

### 🎬 **Step 1: Character Selection**

```
🎬 Welcome to UGC Generator!

=== Character Selection ===
1. Bring your own character
2. Use prebuild characters

Enter your choice (1 or 2): [USER INPUT]
```

**If choice = "1" (Custom Character):**

```
�� You chose to bring your own character
Enter the URL of your character: [USER INPUT - URL]
```

**If choice = "2" (Prebuild Characters):**

```
🎭 You chose to use prebuild characters
Choose from the following characters:
1. Character 1
   URL: https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2PZps4l7vwC1fd4pMXytmhRAYDBUcu3HZNSFo
2. Character 2
   URL: https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2q22n4wMQ9MY3OVAuxjS8dZ04DkcXICptv7Ll
...
9. Character 9
   URL: https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2KUEdHyYhTCsONcWmwFvkrLVfYU43P5AoGMEj

Enter your choice (1-9): [USER INPUT]
```

### ��️ **Step 2: Product Image**

```
=== Product Image ===
Please provide the URL of your product image.

Enter the product image URL: [USER INPUT - URL]
```

### 💬 **Step 3: Dialog Generation**

```
=== Dialog Generation ===
1. Enter custom dialog
2. Auto generate dialog

Enter your choice (1 or 2): [USER INPUT]
```

**If choice = "1" (Custom Dialog):**

```
�� You chose to enter custom dialog
Enter your custom dialog: [USER INPUT - TEXT]
```

**If choice = "2" (Auto Generate):**

```
🤖 You chose to auto generate dialog
```

### 🚀 **Step 4: Plan Execution**

```
🚀 Running Portia plan with Replicate...
```

---

## 📊 **Input Summary Table**

| Step                        | Input Type          | Description                   | Validation                          |
| --------------------------- | ------------------- | ----------------------------- | ----------------------------------- |
| **Character Choice**        | Number (1-2)        | Choose character source       | Must be 1 or 2                      |
| **Character URL/Selection** | URL or Number (1-9) | Custom URL or prebuild choice | URL format or 1-9 range             |
| **Product URL**             | URL                 | Product image URL             | Must start with http:// or https:// |
| **Dialog Choice**           | Number (1-2)        | Choose dialog source          | Must be 1 or 2                      |
| **Custom Dialog**           | Text                | User-provided dialog          | Non-empty string                    |

## �� **Flow Logic**

1. **Character Path**: Custom URL → Validate URL format
2. **Character Path**: Prebuild → Show 9 options → Validate 1-9 range
3. **Product Path**: URL input → Validate URL format
4. **Dialog Path**: Custom text → Validate non-empty
5. **Dialog Path**: Auto-generate → No additional input needed

## �� **Example Complete Flow**

```
🎬 Welcome to UGC Generator!

=== Character Selection ===
1. Bring your own character
2. Use prebuild characters

Enter your choice (1 or 2): 2

🎭 You chose to use prebuild characters
Choose from the following characters:
1. Character 1
   URL: https://m3v8slcorn.ufs.sh/f/pCR9Tew5SdZ2PZps4l7vwC1fd4pMXytmhRAYDBUcu3HZNSFo
...

Enter your choice (1-9): 3

=== Product Image ===
Please provide the URL of your product image.

Enter the product image URL: https://example.com/product.jpg

=== Dialog Generation ===
1. Enter custom dialog
2. Auto generate dialog

Enter your choice (1 or 2): 2

🤖 You chose to auto generate dialog

🚀 Running Portia plan with Replicate...
```
