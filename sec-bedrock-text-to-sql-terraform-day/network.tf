data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${local.name_prefix}-vpc" }
}

resource "aws_subnet" "private" {
  count = 3

  vpc_id            = aws_vpc.this.id
  availability_zone = data.aws_availability_zones.available.names[count.index]
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index)

  tags = { Name = "${local.name_prefix}-private-${count.index + 1}" }
}

resource "aws_security_group" "redshift" {
  name_prefix = "${local.name_prefix}-redshift-"
  description = "Redshift Serverless security group for the private POC workgroup"
  vpc_id      = aws_vpc.this.id

  egress {
    description = "Allow outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name_prefix}-redshift" }
}
