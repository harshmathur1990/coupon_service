-- Create syntax for TABLE 'deleted_vouchers'
CREATE TABLE `deleted_vouchers` (
  `id` binary(16) NOT NULL,
  `code` varchar(20) NOT NULL,
  `rule_id` binary(16) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `from` timestamp NULL DEFAULT NULL,
  `to` timestamp NULL DEFAULT NULL,
  `created_by` binary(16) NOT NULL,
  `updated_by` binary(16) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `rule_id` (`rule_id`),
  CONSTRAINT `deleted_vouchers_ibfk_1` FOREIGN KEY (`rule_id`) REFERENCES `rule` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'freebie_value_list'
CREATE TABLE `freebie_value_list` (
  `rule_id` binary(16) NOT NULL,
  `entity_type` tinyint(3) unsigned NOT NULL,
  `entity_id` bigint(20) unsigned NOT NULL,
  `created_by` binary(16) NOT NULL,
  `updated_by` binary(16) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`rule_id`,`entity_type`,`entity_id`),
  CONSTRAINT `freebie_value_list_ibfk_1` FOREIGN KEY (`rule_id`) REFERENCES `rule` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'item_type_value_list'
CREATE TABLE `item_type_value_list` (
  `rule_id` binary(16) NOT NULL,
  `item_id` bigint(20) unsigned NOT NULL,
  `created_by` binary(16) NOT NULL,
  `updated_by` binary(16) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`rule_id`,`item_id`),
  CONSTRAINT `item_type_value_list_ibfk_1` FOREIGN KEY (`rule_id`) REFERENCES `rule` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'location_value_list'
CREATE TABLE `location_value_list` (
  `rule_id` binary(16) NOT NULL,
  `location_id` bigint(20) unsigned NOT NULL,
  `created_by` binary(16) NOT NULL,
  `updated_by` binary(16) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`rule_id`,`location_id`),
  CONSTRAINT `location_value_list_ibfk_1` FOREIGN KEY (`rule_id`) REFERENCES `rule` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'payment_mode_list'
CREATE TABLE `payment_mode_list` (
  `rule_id` binary(16) NOT NULL,
  `payment_mode` varchar(255) NOT NULL,
  `created_by` binary(16) NOT NULL,
  `updated_by` binary(16) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`rule_id`,`payment_mode`),
  CONSTRAINT `payment_mode_list_ibfk_1` FOREIGN KEY (`rule_id`) REFERENCES `rule` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'rule'
CREATE TABLE `rule` (
  `id` binary(16) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `rule_type` tinyint(3) unsigned NOT NULL,
  `item_type` tinyint(3) unsigned DEFAULT NULL,
  `use_type` tinyint(3) unsigned DEFAULT NULL,
  `no_of_uses_allowed_per_user` int(10) unsigned DEFAULT NULL,
  `no_of_total_uses_allowed` bigint(20) unsigned DEFAULT NULL,
  `range_min` int(10) unsigned DEFAULT NULL,
  `range_max` int(10) unsigned DEFAULT NULL,
  `amount_or_percentage` int(10) unsigned DEFAULT NULL,
  `max_discount_value` int(10) unsigned DEFAULT NULL,
  `location_type` tinyint(3) unsigned DEFAULT NULL,
  `benefit_type` tinyint(3) unsigned DEFAULT NULL,
  `payment_specific` tinyint(1) DEFAULT NULL,
  `active` tinyint(1) DEFAULT NULL,
  `created_by` binary(16) NOT NULL,
  `updated_by` binary(16) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'voucher_use_tracker'
CREATE TABLE `voucher_use_tracker` (
  `id` binary(16) NOT NULL,
  `user_id` binary(16) NOT NULL,
  `applied_on` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `voucher_id` binary(16) NOT NULL,
  `order_id` bigint(20) unsigned NOT NULL,
  PRIMARY KEY (`id`),
  KEY `voucher_id` (`voucher_id`),
  CONSTRAINT `voucher_use_tracker_ibfk_1` FOREIGN KEY (`voucher_id`) REFERENCES `vouchers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'vouchers'
CREATE TABLE `vouchers` (
  `id` binary(16) NOT NULL DEFAULT '\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0',
  `code` varchar(20) NOT NULL,
  `rule_id` binary(16) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `from` timestamp NULL DEFAULT NULL,
  `to` timestamp NULL DEFAULT NULL,
  `created_by` binary(16) NOT NULL,
  `updated_by` binary(16) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`code`),
  UNIQUE KEY `id` (`id`),
  KEY `rule_id` (`rule_id`),
  CONSTRAINT `vouchers_ibfk_1` FOREIGN KEY (`rule_id`) REFERENCES `rule` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;