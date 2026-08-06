# Redshift Serverless has enhanced VPC routing enabled. These resources give
# the private Redshift subnets a no-NAT path to the POC S3 bucket for COPY.
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.this.id

  tags = {
    Name = "${local.name_prefix}-private"
  }
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name = "${local.name_prefix}-s3"
  }
}

output "vpc_id" {
  value = aws_vpc.this.id
}

output "s3_vpc_endpoint_id" {
  value = aws_vpc_endpoint.s3.id
}
