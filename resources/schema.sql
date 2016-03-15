-- Create syntax for TABLE 'all_vouchers'
CREATE TABLE `all_vouchers` (
  `id` binary(16) NOT NULL,
  `code` varchar(20) NOT NULL,
  `rule_id` binary(16) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `from` datetime DEFAULT NULL,
  `to` datetime DEFAULT NULL,
  `created_by` varchar(32) NOT NULL,
  `updated_by` varchar(32) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `rule_id` (`rule_id`),
  CONSTRAINT `all_vouchers_ibfk_1` FOREIGN KEY (`rule_id`) REFERENCES `rule` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'rule'
CREATE TABLE `rule` (
  `id` binary(16) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `rule_type` tinyint(3) unsigned NOT NULL,
  `criteria_json` varchar(8000) NOT NULL,
  `benefits_json` varchar(2000) NOT NULL,
  `sha2hash` varchar(64) DEFAULT NULL,
  `active` tinyint(1) DEFAULT NULL,
  `created_by` varchar(32) NOT NULL,
  `updated_by` varchar(32) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_rule_sha2hash` (`sha2hash`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'user_voucher_transaction_log'
CREATE TABLE `user_voucher_transaction_log` (
  `id` binary(16) NOT NULL,
  `user_id` varchar(32) NOT NULL,
  `updated_on` datetime NOT NULL,
  `voucher_id` binary(16) NOT NULL,
  `order_id` varchar(32) NOT NULL,
  `status` tinyint(3) unsigned NOT NULL,
  PRIMARY KEY (`id`),
  KEY `voucher_id` (`voucher_id`),
  CONSTRAINT `user_voucher_transaction_log_ibfk_1` FOREIGN KEY (`voucher_id`) REFERENCES `all_vouchers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'voucher_use_tracker'
CREATE TABLE `voucher_use_tracker` (
  `id` binary(16) NOT NULL,
  `user_id` varchar(32) NOT NULL,
  `applied_on` datetime NOT NULL,
  `voucher_id` binary(16) NOT NULL,
  `order_id` varchar(32) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `voucher_id` (`voucher_id`),
  CONSTRAINT `voucher_use_tracker_ibfk_1` FOREIGN KEY (`voucher_id`) REFERENCES `all_vouchers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'vouchers'
CREATE TABLE `vouchers` (
  `id` binary(16) NOT NULL,
  `code` varchar(20) NOT NULL,
  `rule_id` binary(16) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `from` datetime DEFAULT NULL,
  `to` datetime DEFAULT NULL,
  `created_by` varchar(32) NOT NULL,
  `updated_by` varchar(32) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`code`),
  UNIQUE KEY `id` (`id`),
  KEY `rule_id` (`rule_id`),
  CONSTRAINT `vouchers_ibfk_1` FOREIGN KEY (`rule_id`) REFERENCES `rule` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;