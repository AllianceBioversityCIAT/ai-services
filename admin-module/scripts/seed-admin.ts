import { createUser, type User } from "../lib/dynamo"
import { hashPassword } from "../lib/auth"

async function seedAdmin() {
  try {
    // Check for required environment variables
    const adminEmail = process.env.ADMIN_EMAIL
    console.log("🚀 ~ seedAdmin ~ adminEmail:", adminEmail)
    const adminPassword = process.env.ADMIN_PASSWORD

    if (!adminEmail || !adminPassword) {
      console.error("Error: ADMIN_EMAIL and ADMIN_PASSWORD environment variables are required")
      process.exit(1)
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(adminEmail)) {
      console.error("Error: ADMIN_EMAIL must be a valid email address")
      process.exit(1)
    }

    // Validate password length
    if (adminPassword.length < 6) {
      console.error("Error: ADMIN_PASSWORD must be at least 6 characters long")
      process.exit(1)
    }

    console.log("Creating admin user...")
    console.log(`Email: ${adminEmail}`)

    // Hash the password
    const passwordHash = await hashPassword(adminPassword)

    // Create admin user object
    const adminUser: User = {
      email: adminEmail.toLowerCase(),
      passwordHash,
      role: "admin",
      createdAt: new Date().toISOString(),
    }
    console.log("🚀 ~ seedAdmin ~ adminUser:", adminUser)

    // Attempt to create the user
    const success = await createUser(adminUser)
    console.log("🚀 ~ seedAdmin ~ success:", success)

    if (success) {
      console.log("✅ Admin user created successfully!")
      console.log(`Admin email: ${adminUser.email}`)
      console.log(`Admin role: ${adminUser.role}`)
      console.log(`Created at: ${adminUser.createdAt}`)
    } else {
      console.log("ℹ️  Admin user already exists")
      console.log(`Email: ${adminUser.email}`)
    }
  } catch (error) {
    console.error("❌ Error creating admin user:", error)
    process.exit(1)
  }
}

// Run the seed function
seedAdmin()
  .then(() => {
    console.log("Admin seeding completed")
    process.exit(0)
  })
  .catch((error) => {
    console.error("Admin seeding failed:", error)
    process.exit(1)
  })
