const axios = require('axios');

const USERS_API_URL = 'http://127.0.0.1:8001/users/';

async function testUserCreation() {
  console.log("Testing user creation API call...");
  try {
    const response = await axios.post(`${USERS_API_URL}?username=test_user`);
    console.log("API call successful!");
    console.log("Response data:", response.data);
  } catch (error) {
    console.error("API call failed!");
    console.error("Error details:", error.response ? error.response.data : error.message);
  }
}

testUserCreation();