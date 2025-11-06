# AICCRA Report Generator Web UI

This web interface provides an easy and intuitive way to generate AICCRA reports without requiring technical knowledge or direct API calls.

## 🌐 Accessing the UI

Once the FastAPI server is running, you can access the web interface at:

- **Local development**: `http://localhost:8000/web/`
- **Production**: `https://ia.prms.cgiar.org/web/`

## ✨ Features

### 📊 Annual Reports by Indicator
- Generate comprehensive annual reports for specific indicators
- Supports all IPI (1.1-3.4) and PDO (1-5) indicators
- Includes progress analysis, achievements, and recommendations
- Download available in DOCX format

### 📋 Indicator Summary Tables
- Generate consolidated tables for all indicators grouped by type
- Includes targets, achievements, and AI-generated summaries
- Individual download by group in Excel format
- Responsive tabular view for easy review

### 🎯 Challenges and Lessons Learned Reports
- Cross-cluster analysis of all clusters
- Identifies implementation challenges and adaptive strategies
- Synthesizes best practices and strategic recommendations
- Focus on organizational learning and adaptive management

## 🛠️ Technical Features

### Technologies Used
- **HTML5 & CSS3**: Modern responsive interface
- **JavaScript ES6+**: Interactive functionality
- **Font Awesome**: Iconography
- **Google Fonts**: Typography (Inter)

### Color Palette
- **Primary Blue**: `#0478A3` - Headers and main elements
- **Medium Blue**: `#3A84A7` - Secondary elements
- **Light Blue**: `#81B8C1` - Borders and supporting elements
- **Very Light Blue**: `#E7F4FF` - Backgrounds and highlighted areas
- **CGIAR Yellow**: `#FFCD2A` - Accent elements
- **Green**: `#8CBF3F` - Success states
- **Orange**: `#F39820` - Alerts and warnings

### Key Functionalities
- **Automatic URL Detection**: Automatically adapts between development and production
- **State Management**: Loading states, error handling, and visual feedback
- **File Downloads**: Export to DOCX and Excel
- **Tab Interface**: Intuitive navigation between different report types
- **Responsive Design**: Works on desktop, tablet, and mobile

## 🚀 Usage

1. **Access the interface** by navigating to `/web/` on your server
2. **Select report type** using the top tabs
3. **Configure parameters** (indicator, year) according to report type
4. **Generate the report** by clicking the corresponding button
5. **Review results** in the interface
6. **Download** the report in your desired format

## 📁 File Structure

```
web/
├── index.html          # Main page structure
├── app.js              # JavaScript logic and API calls
└── README.md           # UI documentation
```

## 🐛 Troubleshooting

### API Connection Error
- Verify that the FastAPI server is running
- Confirm that the API URL is correct
- Check CORS configuration if there are cross-origin issues

### Report Generation Errors
- Verify that backend services (OpenSearch, SQL Server, AWS Bedrock) are available
- Confirm that parameters (indicator, year) are valid
- Check server logs for error details

### Download Issues
- Verify that the browser allows downloads
- Confirm that the report was generated successfully before attempting download
- Some pop-up blockers may interfere with downloads

## 🔄 Updates

To update the UI:
1. Modify HTML/CSS/JS files as needed
2. Changes are reflected immediately (no server restart required)
3. Browser cache may require forced refresh (Ctrl+F5)

## 📞 Support

For web interface issues, contact:
- **Email**: MARLOSupport@cgiar.org
- **URL**: https://aiccra.marlo.cgiar.org/