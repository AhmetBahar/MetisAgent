-- MetisAgent3 Plugin Registry Tables
-- Database: METISENGINE on metissqldb.database.windows.net

-- 1. Main plugins table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='plugins' AND xtype='U')
CREATE TABLE plugins (
    plugin_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    name NVARCHAR(100) NOT NULL UNIQUE,
    display_name NVARCHAR(200),
    version NVARCHAR(50) NOT NULL,
    plugin_type NVARCHAR(50) NOT NULL,  -- python_module, api, executable
    blob_path NVARCHAR(500) NOT NULL,
    status NVARCHAR(50) DEFAULT 'active',
    is_enabled BIT DEFAULT 1,
    manifest_json NVARCHAR(MAX),
    tool_config_json NVARCHAR(MAX),
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    updated_at DATETIME2 DEFAULT GETUTCDATE()
);
GO

-- 2. Plugin capabilities table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='plugin_capabilities' AND xtype='U')
CREATE TABLE plugin_capabilities (
    capability_id UNIQUEIDENTIFIER PRIMARY KEY DEFAULT NEWID(),
    plugin_id UNIQUEIDENTIFIER REFERENCES plugins(plugin_id) ON DELETE CASCADE,
    name NVARCHAR(200) NOT NULL,
    capability_type NVARCHAR(50),  -- read, write, execute
    description NVARCHAR(MAX)
);
GO

-- 3. User plugin access table
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_plugin_access' AND xtype='U')
CREATE TABLE user_plugin_access (
    user_id NVARCHAR(100),
    plugin_id UNIQUEIDENTIFIER REFERENCES plugins(plugin_id) ON DELETE CASCADE,
    is_enabled BIT DEFAULT 1,
    PRIMARY KEY (user_id, plugin_id)
);
GO

-- Create indexes for performance
CREATE INDEX IX_plugins_name ON plugins(name);
CREATE INDEX IX_plugins_status ON plugins(status);
CREATE INDEX IX_plugin_capabilities_plugin_id ON plugin_capabilities(plugin_id);
CREATE INDEX IX_user_plugin_access_user_id ON user_plugin_access(user_id);
GO

PRINT 'Plugin registry tables created successfully!';
GO
